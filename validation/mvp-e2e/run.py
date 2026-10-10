"""Orquestador de la validación integral del MVP (017).

Contrato: `specs/017-mvp-integral-validation/contracts/runner-cli.md`.

Etapas en orden fijo: preflight → recorrido → seguridad → caidas → guia → regresion. Cada etapa de
pytest se ejecuta en su propio proceso con su JUnit; todas comparten el `RUN_ID` y el directorio
`reports/<RUN_ID>/`. Al empezar se guarda el estado de los contenedores gestionados y al terminar
(también ante error, `Ctrl+C` o señal) se arrancan los que quedaron detenidos.
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SUITE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SUITE_DIR))

from sio_mvp import config, report  # noqa: E402
from sio_mvp.docker_env import DockerEnv  # noqa: E402
from sio_mvp.run_context import RunContext, new_run_id  # noqa: E402

REPORTS_DIR = SUITE_DIR / "reports"
GAP_REGISTER = config.REPO_ROOT / "specs" / "017-mvp-integral-validation" / "gap-register.md"

PYTEST_STAGES = {
    "preflight": ["tests/test_00_preflight.py"],
    "recorrido": ["tests/test_10_recorrido.py", "tests/test_20_auditoria.py"],
    "seguridad": ["tests/test_30_seguridad.py"],
    "caidas": ["tests/test_40_caidas.py"],
    "guia": ["tests/test_50_guia.py"],
}
ORDER = ("preflight", "recorrido", "seguridad", "caidas", "guia", "regresion")
DEFAULT_STAGES = ("preflight", "recorrido", "seguridad", "caidas", "guia")
# Etapas que necesitan el mundo de la corrida (configuración del recorrido).
NEEDS_RECORRIDO = {"seguridad", "caidas", "guia"}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_head() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=config.REPO_ROOT, capture_output=True, text=True, timeout=10
        )
        return completed.stdout.strip() or "desconocido"
    except (OSError, subprocess.SubprocessError):
        return "desconocido"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run.sh", description="Validación integral del MVP de SIO (017).")
    parser.add_argument("--todo", action="store_true", help="Todas las etapas, incluida la regresión (gate).")
    parser.add_argument("--etapa", action="append", choices=ORDER, default=[], help="Ejecuta solo esta etapa.")
    parser.add_argument("--linea-base", action="store_true", help="Toma la línea base de la regresión.")
    parser.add_argument("--restaurar", action="store_true", help="Solo arranca contenedores gestionados detenidos.")
    parser.add_argument("--sin-caidas", action="store_true", help="Omite la etapa caidas.")
    args = parser.parse_args(argv)
    if args.todo and args.etapa:
        parser.error("--todo y --etapa son excluyentes")
    return args


def selected_stages(args: argparse.Namespace) -> list[str]:
    if args.todo:
        stages = list(ORDER)
    elif args.etapa:
        stages = ["preflight", *args.etapa]
    else:
        stages = list(DEFAULT_STAGES)
    if args.sin_caidas:
        stages = [stage for stage in stages if stage != "caidas"]
    return [stage for stage in ORDER if stage in stages]


def read_gaps(path: Path = GAP_REGISTER) -> list[dict]:
    """Lee `gap-register.md` (contracts/gap-classification.md §2): filas `| G-017-NN | … |`."""
    if not path.is_file():
        return []
    gaps = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or not re.fullmatch(r"G-017-\d+", cells[0]):
            continue
        text = " ".join(cells).upper()
        classification = "NO BLOQUEANTE" if "NO BLOQUEANTE" in text else ("BLOQUEANTE" if "BLOQUEANTE" in text else "SIN CLASIFICAR")
        status = "CERRADA" if "CERRADA" in text else "ABIERTA"
        gaps.append(
            {
                "id": cells[0],
                "item": cells[1] if len(cells) > 1 else "",
                "description": cells[3] if len(cells) > 3 else "",
                "classification": classification,
                "status": status,
            }
        )
    return gaps


class Orchestrator:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.context = RunContext(os.environ.get("SIO_MVP_RUN_ID") or new_run_id())
        self.report_dir = REPORTS_DIR / self.context.run_id
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.docker = DockerEnv()
        self.snapshot: dict = {}
        self.restored_once = False
        self.restore_report = None
        self.timings: dict[str, float] = {}
        self.stage_results: dict[str, str] = {}
        self.stages: list[str] = []

    # --- restauración garantizada -------------------------------------------------------------
    def take_snapshot(self) -> None:
        self.snapshot = self.docker.snapshot(config.managed_containers())
        (self.report_dir / "containers-start.json").write_text(
            json.dumps({name: state.__dict__ for name, state in self.snapshot.items()}, indent=2), encoding="utf-8"
        )

    def restore(self) -> None:
        if self.restored_once or not self.snapshot:
            return
        self.restored_once = True
        self.restore_report = self.docker.restore_all(self.snapshot)
        if self.restore_report.restored:
            print(f"==> Restaurados: {', '.join(self.restore_report.restored)}", file=sys.stderr)
        if self.restore_report.failed:
            print(f"==> SIN RESTAURAR: {', '.join(self.restore_report.failed)}", file=sys.stderr)

    def environment_restored(self) -> bool:
        if self.restore_report is not None and not self.restore_report.ok:
            return False
        for name, before in self.snapshot.items():
            if before.healthy and self.docker.inspect(name).status != "running":
                return False
        return True

    def install_handlers(self) -> None:
        atexit.register(self.restore)

        def handler(signum, frame):  # noqa: ARG001
            raise KeyboardInterrupt(f"señal {signum}")

        for name in ("SIGINT", "SIGTERM", "SIGHUP"):
            if hasattr(signal, name):
                signal.signal(getattr(signal, name), handler)

    # --- etapas -------------------------------------------------------------------------------
    def stage_env(self, stage: str) -> dict[str, str]:
        environ = dict(os.environ)
        environ.update(
            {
                "SIO_MVP_RUN_ID": self.context.run_id,
                "SIO_MVP_REPORT_DIR": str(self.report_dir),
                "SIO_MVP_STAGE": stage,
                "SIO_MVP_STAGES": ",".join(self.stages),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        return environ

    def run_pytest_stage(self, stage: str) -> str:
        files = [path for path in PYTEST_STAGES[stage] if (SUITE_DIR / path).is_file()]
        command = [
            sys.executable,
            "-m",
            "pytest",
            *files,
            "-p",
            "no:cacheprovider",
            "-rA" if stage == "preflight" else "-ra",
            "--junitxml",
            str(self.report_dir / f"pytest-{stage}.xml"),
        ]
        print(f"\n==> Etapa {stage} (RUN_ID {self.context.run_id})", file=sys.stderr)
        completed = subprocess.run(command, cwd=SUITE_DIR, env=self.stage_env(stage))
        if completed.returncode == 0:
            return "CUMPLE"
        if completed.returncode == 5:  # sin pruebas recolectadas
            return "NO CUMPLE"
        return "NO CUMPLE"

    def run_regression_stage(self) -> str:
        from sio_mvp import regression

        print(f"\n==> Etapa regresion (RUN_ID {self.context.run_id})", file=sys.stderr)
        result = regression.run_stage(self.report_dir, settings=config.load_settings(), docker=self.docker)
        return "CUMPLE" if result.ok else "NO CUMPLE"

    def world_exists(self) -> bool:
        return (self.report_dir / "world.json").is_file()

    def run_stages(self, stages: list[str]) -> None:
        for stage in stages:
            if stage != "preflight" and self.stage_results.get("preflight") != "CUMPLE":
                self.stage_results[stage] = "BLOQUEADA"
                continue
            started = time.monotonic()
            if stage == "regresion":
                result = self.run_regression_stage()
            else:
                result = self.run_pytest_stage(stage)
            self.timings[stage] = round(time.monotonic() - started, 1)
            self.stage_results[stage] = result
            if stage == "preflight" and result != "CUMPLE":
                print("==> preflight falló: el entorno no cumple las precondiciones (código 2).", file=sys.stderr)

    # --- ítems --------------------------------------------------------------------------------
    def item_results(self) -> dict[int, dict]:
        collected: dict[int, dict] = {}
        for path in sorted(self.report_dir.glob("items-*.json")):
            for entry in json.loads(path.read_text(encoding="utf-8")):
                item = collected.setdefault(entry["item"], {"tests": [], "outcomes": [], "evidence": []})
                item["tests"].append(entry["test"])
                item["outcomes"].append(entry["outcome"])
                item["evidence"].extend(entry.get("evidence", []))
        results: dict[int, dict] = {}
        for item in report.ITEMS:
            stage_result = self.stage_results.get(item.stage)
            data = collected.get(item.number)
            if item.stage == "regresion":
                result = {"CUMPLE": "CUMPLE", "NO CUMPLE": "NO CUMPLE", "BLOQUEADA": "BLOQUEADO"}.get(
                    stage_result or "", "NO EJECUTADO"
                )
                results[item.number] = {"result": result, "tests": ["regresion"], "evidence": ["regression.json"]}
                continue
            if stage_result is None:
                results[item.number] = {"result": "NO EJECUTADO"}
                continue
            if stage_result == "BLOQUEADA":
                results[item.number] = {"result": "BLOQUEADO"}
                continue
            if not data:
                results[item.number] = {"result": "NO CUMPLE" if stage_result else "NO EJECUTADO"}
                continue
            outcomes = data["outcomes"]
            if any(outcome == "failed" for outcome in outcomes):
                result = "NO CUMPLE"
            elif any(outcome == "blocked" for outcome in outcomes):
                result = "BLOQUEADO"
            elif all(outcome == "passed" for outcome in outcomes):
                result = "CUMPLE"
            else:
                result = "NO CUMPLE"
            results[item.number] = {
                "result": result,
                "tests": sorted(set(data["tests"])),
                "evidence": sorted(set(data["evidence"])),
            }
        return results

    def merged_timings(self) -> dict[str, float]:
        timings = dict(self.timings)
        for path in sorted(self.report_dir.glob("timings-*.json")):
            timings.update(json.loads(path.read_text(encoding="utf-8")))
        return timings

    # --- modos --------------------------------------------------------------------------------
    def main(self) -> int:
        started_at = now()
        started = time.monotonic()
        args = self.args
        (self.report_dir / "run.json").write_text(
            json.dumps(
                {
                    "run_id": self.context.run_id,
                    "run_uuid": str(self.context.run_uuid),
                    "started_at": started_at,
                    "git_head": git_head(),
                    "arguments": sys.argv[1:],
                    "urls": dict(config.load_settings().urls),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        self.install_handlers()
        self.take_snapshot()

        if args.restaurar:
            self.restore()
            restored = self.environment_restored()
            print(f"==> Entorno {'restaurado' if restored else 'NO restaurado'}", file=sys.stderr)
            return 0 if restored else 3

        if args.linea_base:
            from sio_mvp import regression

            try:
                baseline = regression.take_baseline(
                    self.report_dir, settings=config.load_settings(), docker=self.docker
                )
            finally:
                self.restore()
            print(f"==> Línea base escrita en {regression.BASELINE_PATH} ({baseline.summary_line()})", file=sys.stderr)
            return 0 if self.environment_restored() else 3

        stages = selected_stages(args)
        self.stages = stages
        try:
            self.run_stages(stages)
        except KeyboardInterrupt:
            print("\n==> Interrumpido: restaurando el entorno", file=sys.stderr)
            for stage in stages:
                self.stage_results.setdefault(stage, "BLOQUEADA")
        finally:
            self.restore()
        restored = self.environment_restored()
        self.timings["total"] = round(time.monotonic() - started, 1)
        data = report.build_summary(
            run_id=self.context.run_id,
            started_at=started_at,
            finished_at=now(),
            git_head=git_head(),
            todo=bool(args.todo),
            stages=self.stage_results,
            item_results=self.item_results(),
            gaps=read_gaps(),
            environment_restored=restored,
            timings=self.merged_timings(),
            restored_containers=self.restore_report.restored if self.restore_report else [],
            unrestored_containers=self.restore_report.failed if self.restore_report else [],
        )
        report.write(self.report_dir, data)
        code = report.exit_code(
            preflight_ok=self.stage_results.get("preflight") == "CUMPLE",
            stages=self.stage_results,
            environment_restored=restored,
        )
        print(
            f"\n==> RUN_ID {self.context.run_id}: "
            + ", ".join(f"{stage}={result}" for stage, result in data["stages"].items())
            + f"; gate_eligible={str(data['gate_eligible']).lower()}; código {code}",
            file=sys.stderr,
        )
        print(f"==> Informe: {self.report_dir / 'summary.md'}", file=sys.stderr)
        return code


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    return Orchestrator(args).main()


if __name__ == "__main__":
    sys.exit(main())
