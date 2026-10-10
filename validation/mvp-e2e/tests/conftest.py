"""Sesión de la suite E2E: contexto de la corrida, diario, clientes, Docker y mundo.

Cada etapa se ejecuta en su propio proceso (run.py) con `SIO_MVP_RUN_ID`, `SIO_MVP_REPORT_DIR` y
`SIO_MVP_STAGE`. Las pruebas declaran los ítems de la FASE 10 que sustentan con
`@pytest.mark.items(…)`; al terminar, el resultado por ítem queda en `items-<etapa>.json` (resumen).
"""

from __future__ import annotations

import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

import pytest

from sio_mvp import config as sio_config
from sio_mvp.auth import Clients
from sio_mvp.docker_env import DockerEnv
from sio_mvp.journal import Journal
from sio_mvp.realm import realm as load_realm
from sio_mvp.run_context import RunContext, new_run_id

SUITE_DIR = Path(__file__).resolve().parents[1]
BLOCKED_PREFIX = "BLOQUEADO"


def pytest_configure(config):
    config.addinivalue_line("markers", "items(*numbers): ítems de la FASE 10 que sustenta la prueba")
    config.addinivalue_line("markers", "evidence(*refs): evidencia adicional (step_id o archivo)")



def _stage() -> str:
    return os.environ.get("SIO_MVP_STAGE", "manual")


def _report_dir() -> Path:
    run_id = os.environ.setdefault("SIO_MVP_RUN_ID", new_run_id())
    path = Path(os.environ.get("SIO_MVP_REPORT_DIR") or SUITE_DIR / "reports" / run_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


# --- resultados por ítem ---------------------------------------------------------------------
_ITEM_RESULTS: list[dict] = []


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    marker = item.get_closest_marker("items")
    if marker is None:
        return
    if report.when == "call" or (report.when == "setup" and report.outcome != "passed"):
        if report.passed:
            result = "passed"
        elif report.skipped:
            reason = str(report.longrepr[-1]) if isinstance(report.longrepr, tuple) else str(report.longrepr)
            result = "blocked" if BLOCKED_PREFIX in reason else "skipped"
        else:
            result = "failed"
        evidence_marker = item.get_closest_marker("evidence")
        evidence = list(evidence_marker.args) if evidence_marker else []
        for number in marker.args:
            _ITEM_RESULTS.append({"item": number, "test": item.nodeid, "outcome": result, "evidence": evidence})


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    if "SIO_MVP_STAGE" not in os.environ and not _ITEM_RESULTS:
        return  # pruebas unitarias o colección: sin informe
    path = _report_dir() / f"items-{_stage()}.json"
    path.write_text(json.dumps(_ITEM_RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")


# --- fixtures de sesión ----------------------------------------------------------------------
@pytest.fixture(scope="session")
def settings() -> sio_config.Settings:
    return sio_config.load_settings()


@pytest.fixture(scope="session")
def run_context() -> RunContext:
    _report_dir()
    return RunContext(os.environ["SIO_MVP_RUN_ID"])


@pytest.fixture(scope="session")
def report_dir() -> Path:
    return _report_dir()


@pytest.fixture(scope="session")
def journal(settings, report_dir) -> Journal:
    return Journal(report_dir, sensitive_values=settings.sensitive_values())


@pytest.fixture(scope="session")
def clients(settings, run_context, journal) -> Clients:
    return Clients(settings, run_context, journal, stage=_stage())


@pytest.fixture(scope="session")
def docker() -> DockerEnv:
    return DockerEnv()


@pytest.fixture(scope="session")
def realm():
    return load_realm()


class Timer:
    """Tiempos informativos por macroetapa (R-14) en `timings-<etapa>.json`."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.values: dict[str, float] = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    @contextmanager
    def measure(self, name: str):
        started = time.monotonic()
        try:
            yield
        finally:
            self.values[name] = round(self.values.get(name, 0.0) + time.monotonic() - started, 1)
            self.path.write_text(json.dumps(self.values, ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture(scope="session")
def timer(report_dir) -> Timer:
    return Timer(report_dir / f"timings-{_stage()}.json")


@pytest.fixture(scope="session")
def world(settings, run_context, journal, clients, report_dir, timer):
    """Mundo de la corrida (C-01..C-13). Se construye una vez por corrida y se comparte por `world.json`."""
    from scenario.world import load_or_build, persist

    with timer.measure("recorrido.configuracion" if _stage() == "recorrido" else f"{_stage()}.mundo"):
        built = load_or_build(settings=settings, context=run_context, journal=journal, clients=clients, report_dir=report_dir)
    yield built
    persist(built, report_dir)
    if journal.expected_audits:  # nunca sobrescribir con una lista vacía (repeticiones de una etapa)
        journal.write_expected_audit()
