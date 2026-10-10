"""Regresión integral: suites de los 10 servicios y de `libs/`, en serie (research R-13).

Por servicio: `pytest` completo (configuración por defecto del servicio, incluye `tests/examples`),
`pytest -m integration` y, donde el marcador existe, `pytest -m performance`. Por librería: `pytest`
completo y `-m integration` si lo declara. Cada suite se ejecuta con el intérprete del `.venv` del
servicio y una configuración solo del proceso (URL de la base de pruebas desde `infrastructure/.env`,
URL de integración en `127.0.0.1` donde la prueba trae puertos antiguos). Nunca en paralelo.

Las pruebas de integración de los servicios detienen y reinician contenedores; después de cada suite se
arranca cualquier contenedor gestionado que haya quedado detenido.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .docker_env import DockerEnv

SUITE_DIR = Path(__file__).resolve().parents[1]
BASELINE_PATH = SUITE_DIR / "baseline.json"
SUITE_TIMEOUT_SECONDS = 3 * 3600

# Los 6 fallos conocidos de Geography (`list_all()`, GAP registrado en su backlog).
KNOWN_GEOGRAPHY_FAILURES = (
    "tests.contract.test_global_administrative_division_repository::test_list_all_returns_divisions_ordered_by_name",
    "tests.contract.test_global_city_repository::test_list_all_returns_cities_ordered_by_name",
    "tests.contract.test_global_country_repository::test_list_all_returns_countries_ordered_by_name",
    "tests.unit.test_global_administrative_division_service::test_list_all_returns_repository_divisions",
    "tests.unit.test_global_city_service::test_list_all_returns_repository_cities",
    "tests.unit.test_global_country_service::test_list_all_returns_repository_countries",
)


@dataclass(frozen=True)
class Target:
    key: str  # p. ej. "sales" o "libs/sio-audit"
    directory: Path
    prefix: str | None  # prefijo de las variables *_TEST_DB_* en infrastructure/.env

    @property
    def markers(self) -> set[str]:
        path = self.directory / "pyproject.toml"
        if not path.is_file():
            return set()
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        declared = data.get("tool", {}).get("pytest", {}).get("ini_options", {}).get("markers", [])
        return {entry.split(":", 1)[0].strip() for entry in declared}

    def python(self) -> Path | None:
        for candidate in (self.directory / ".venv" / "bin" / "python", self.directory / ".venv" / "Scripts" / "python.exe"):
            if candidate.exists():
                return candidate
        return None

    def suites(self) -> list[str]:
        markers = self.markers
        suites = ["full"]
        if "integration" in markers:
            suites.append("integration")
        if "performance" in markers:
            suites.append("performance")
        return suites


def targets() -> list[Target]:
    items = [Target(service.key, service.source_dir, service.env_name) for service in config.SERVICES]
    items.append(Target("libs/sio-audit", config.REPO_ROOT / "libs" / "sio-audit", None))
    items.append(Target("libs/sio-auth", config.REPO_ROOT / "libs" / "sio-auth", None))
    return items


def _database_url(settings: config.Settings, prefix: str, *, test: bool) -> str | None:
    kind = "TEST_DB" if test else "DB"
    user = settings.value(f"{prefix}_{kind}_USER")
    name = settings.value(f"{prefix}_{kind}_NAME")
    port = settings.value(f"{prefix}_{kind}_PORT")
    password = settings.secret(f"{prefix}_{kind}_PASSWORD")
    if not (user and name and port and password):
        return None
    return f"postgresql+psycopg://{user}:{password.reveal()}@127.0.0.1:{port}/{name}"


def process_environment(target: Target, settings: config.Settings) -> dict[str, str]:
    """Configuración solo del proceso de la suite (nunca se escribe en disco ni se imprime)."""
    environ = dict(os.environ)
    environ.pop("VIRTUAL_ENV", None)
    environ["PYTHONDONTWRITEBYTECODE"] = "1"
    if target.prefix:
        url = _database_url(settings, target.prefix, test=True)
        if url:
            environ[f"{target.prefix}_TEST_DATABASE_URL"] = url
    if target.key == "geography":
        url = _database_url(settings, "GEOGRAPHY", test=False)
        if url:
            environ.setdefault("DATABASE_URL", url)
    if target.key == "party-identity":
        # test_phase_b_integration trae por defecto los puertos del entorno retirado (8002/8004/8000).
        environ["PARTY_IDENTITY_INTEGRATION_BASE_URL"] = settings.service_url("party-identity")
        environ["OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL"] = settings.service_url("operational-context")
        environ["GEOGRAPHY_SERVICE_BASE_URL"] = settings.service_url("geography")
    if target.key == "libs/sio-audit":
        url = _database_url(settings, "AUDIT", test=True)
        if url:
            environ["SIO_AUDIT_TEST_DATABASE_URL"] = url
    return environ


@dataclass
class SuiteResult:
    target: str
    suite: str
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    total: int = 0
    failures: list[str] = field(default_factory=list)  # fallos y errores por identificador
    duration_seconds: float = 0.0
    exit_code: int | None = None
    note: str = ""

    @property
    def ok(self) -> bool:
        return self.failed == 0 and self.errors == 0 and self.exit_code in (0, 5)


def parse_junit(path: Path, target: str, suite: str) -> SuiteResult:
    result = SuiteResult(target, suite)
    if not path.is_file():
        result.note = "sin JUnit"
        return result
    root = ET.parse(path).getroot()
    for case in root.iter("testcase"):
        result.total += 1
        identifier = f"{case.get('classname', '')}::{case.get('name', '')}"
        if case.find("failure") is not None:
            result.failed += 1
            result.failures.append(identifier)
        elif case.find("error") is not None:
            result.errors += 1
            result.failures.append(identifier)
        elif case.find("skipped") is not None:
            result.skipped += 1
        else:
            result.passed += 1
    result.failures.sort()
    return result


def suite_command(python: Path, suite: str, junit: Path) -> list[str]:
    command = [str(python), "-m", "pytest", "-p", "no:cacheprovider", "-q", "--junitxml", str(junit)]
    if suite != "full":
        command += ["-m", suite, "-o", "addopts="]
    return command


def ensure_test_databases(docker: DockerEnv, settings: config.Settings) -> list[str]:
    """Levanta las bases de pruebas (perfil `test`) que falten (E-11)."""
    started = []
    for service in config.SERVICES:
        if docker.inspect(service.test_db_container).healthy:
            continue
        compose = config.REPO_ROOT / "infrastructure" / "services" / f"{service.project}.yaml"
        env_file = config.REPO_ROOT / "infrastructure" / ".env"
        code, output = docker.run(
            [
                "compose",
                "--project-name",
                service.project,
                "--file",
                str(compose),
                "--env-file",
                str(env_file),
                "--profile",
                "test",
                "up",
                "-d",
                "--wait",
                f"{service.key}-test-db",
            ]
        )
        if code != 0:
            raise RuntimeError(f"No se pudo levantar {service.test_db_container}: {output.strip()[-300:]}")
        started.append(service.test_db_container)
    return started


def run_suite(target: Target, suite: str, settings: config.Settings, out_dir: Path) -> SuiteResult:
    python = target.python()
    if python is None:
        return SuiteResult(target.key, suite, exit_code=None, note="sin .venv")
    safe = target.key.replace("/", "-")
    junit = out_dir / f"junit-{safe}-{suite}.xml"
    log = out_dir / f"log-{safe}-{suite}.txt"
    started = time.monotonic()
    print(f"    {target.key} [{suite}]", file=sys.stderr, flush=True)
    with log.open("w", encoding="utf-8") as handle:
        try:
            completed = subprocess.run(
                suite_command(python, suite, junit),
                cwd=target.directory,
                env=process_environment(target, settings),
                stdout=handle,
                stderr=subprocess.STDOUT,
                timeout=SUITE_TIMEOUT_SECONDS,
            )
            code: int | None = completed.returncode
            note = ""
        except subprocess.TimeoutExpired:
            code, note = None, f"límite de {SUITE_TIMEOUT_SECONDS} s"
    result = parse_junit(junit, target.key, suite)
    result.exit_code = code
    result.duration_seconds = round(time.monotonic() - started, 1)
    result.note = result.note or note
    if code not in (0, 1, 5) and not result.note:
        result.note = f"pytest terminó con código {code}"
    print(
        f"      passed={result.passed} failed={result.failed} errors={result.errors} skipped={result.skipped} "
        f"({result.duration_seconds:.0f} s){' ' + result.note if result.note else ''}",
        file=sys.stderr,
        flush=True,
    )
    return result


@dataclass
class RegressionRun:
    taken_at: str
    git_head: str
    results: list[SuiteResult]
    test_databases_started: list[str]
    containers_restored: list[str]

    def summary_line(self) -> str:
        failed = sum(item.failed + item.errors for item in self.results)
        total = sum(item.total for item in self.results)
        return f"{len(self.results)} suites, {total} pruebas, {failed} fallos o errores"

    def as_dict(self) -> dict:
        grouped: dict[str, dict] = {}
        for item in self.results:
            data = asdict(item)
            data.pop("target")
            suite = data.pop("suite")
            grouped.setdefault(item.target, {})[suite] = data
        return {
            "taken_at": self.taken_at,
            "git_head": self.git_head,
            "known_failures": {"geography": list(KNOWN_GEOGRAPHY_FAILURES)},
            "test_databases_started": self.test_databases_started,
            "containers_restored": self.containers_restored,
            "results": grouped,
        }


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=config.REPO_ROOT, capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "desconocido"


def execute(report_dir: Path, *, settings: config.Settings, docker: DockerEnv) -> RegressionRun:
    out_dir = Path(report_dir) / "regression"
    out_dir.mkdir(parents=True, exist_ok=True)
    started_dbs = ensure_test_databases(docker, settings)
    snapshot = docker.snapshot(config.managed_containers())
    results: list[SuiteResult] = []
    restored: list[str] = []
    for target in targets():
        for suite in target.suites():
            results.append(run_suite(target, suite, settings, out_dir))
            # Las pruebas de integración detienen contenedores; se deja todo como al inicio.
            report = docker.restore_all(snapshot)
            restored += [f"{target.key}[{suite}]:{name}" for name in report.restored]
            restored += [f"{target.key}[{suite}]:FALLÓ:{name}" for name in report.failed]
    return RegressionRun(
        taken_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        git_head=_git_head(),
        results=results,
        test_databases_started=started_dbs,
        containers_restored=restored,
    )


def take_baseline(report_dir: Path, *, settings: config.Settings, docker: DockerEnv) -> RegressionRun:
    run = execute(report_dir, settings=settings, docker=docker)
    BASELINE_PATH.write_text(json.dumps(run.as_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return run


# --- comparación con la línea base (T055) ------------------------------------------------------------
@dataclass
class Comparison:
    items: list[dict]
    alerts: list[str]

    @property
    def ok(self) -> bool:
        return all(item["ok"] for item in self.items) and not any(alert.startswith("SIN EJECUTAR") for alert in self.alerts)

    def write(self, directory: Path) -> Path:
        path = Path(directory) / "regression.json"
        path.write_text(
            json.dumps({"ok": self.ok, "alerts": self.alerts, "items": self.items}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path


def _counts(data: dict) -> dict:
    return {key: data.get(key) for key in ("passed", "failed", "errors", "skipped", "total", "exit_code")}


def compare(baseline: dict, results: list[SuiteResult]) -> Comparison:
    """Fallo conocido igual → no es regresión; fallo nuevo → regresión; menos pruebas → alerta."""
    items: list[dict] = []
    alerts: list[str] = []
    seen: set[tuple[str, str]] = set()
    for result in results:
        seen.add((result.target, result.suite))
        before = baseline.get("results", {}).get(result.target, {}).get(result.suite)
        before_failures = set(before.get("failures", [])) if before else set()
        after_failures = set(result.failures)
        new_failures = sorted(after_failures - before_failures)
        item_alerts = []
        if before is None:
            item_alerts.append("sin línea base para esta suite")
        elif result.total < (before.get("total") or 0):
            item_alerts.append(f"menos pruebas que la línea base ({result.total} < {before['total']})")
        abnormal = result.exit_code not in (0, 1, 5)
        if abnormal:
            item_alerts.append(f"ejecución anómala (código {result.exit_code}{', ' + result.note if result.note else ''})")
        items.append(
            {
                "target": result.target,
                "suite": result.suite,
                "before": _counts(before or {}),
                "after": _counts(asdict(result)),
                "new_failures": new_failures,
                "known_failures": sorted(after_failures & before_failures),
                "fixed": sorted(before_failures - after_failures),
                "alerts": item_alerts,
                "ok": not new_failures and not abnormal,
                "duration_seconds": result.duration_seconds,
            }
        )
        alerts += [f"{result.target}/{result.suite}: {alert}" for alert in item_alerts]
    for target, suites in baseline.get("results", {}).items():
        for suite in suites:
            if (target, suite) not in seen:
                alerts.append(f"SIN EJECUTAR {target}/{suite}: está en la línea base y no se ejecutó")
    return Comparison(items, alerts)


def unexpected_baseline_failures(baseline: dict) -> dict[str, list[str]]:
    """Fallos de la línea base distintos de los 6 conocidos de Geography (T020: detenerse y consultar)."""
    known = set(KNOWN_GEOGRAPHY_FAILURES)
    unexpected: dict[str, list[str]] = {}
    for target, suites in baseline.get("results", {}).items():
        for suite, data in suites.items():
            failures = [item for item in data.get("failures", []) if not (target == "geography" and item in known)]
            if failures:
                unexpected[f"{target}/{suite}"] = failures
    return unexpected


@dataclass
class StageResult:
    ok: bool
    comparison: Comparison


def run_stage(report_dir: Path, *, settings: config.Settings, docker: DockerEnv) -> StageResult:
    """Etapa `regresion`: ejecuta todo y compara con `baseline.json` (escribe `regression.json`)."""
    if not BASELINE_PATH.is_file():
        raise RuntimeError("Falta validation/mvp-e2e/baseline.json: ejecute primero run.sh --linea-base")
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    run = execute(report_dir, settings=settings, docker=docker)
    comparison = compare(baseline, run.results)
    comparison.write(report_dir)
    return StageResult(comparison.ok, comparison)
