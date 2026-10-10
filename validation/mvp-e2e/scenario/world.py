"""Mundo de la corrida (data-model §3.1) construido por API con los pasos C-00..C-13 de `steps.py`.

El mundo se construye una vez por corrida y se comparte entre etapas por `reports/<RUN_ID>/world.json`,
que solo guarda ids, versiones y fechas: los números de identificación (variables `nit_*`, `cc_*`) no se
escriben nunca. Una etapa que carga el mundo vuelve a registrar esos valores protegidos en su diario
leyéndolos de Party Identity, para filtrarlos de sus informes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from scenario import steps as catalogue
from scenario.steps import Runner, StepFailed, is_protected
from sio_mvp.auth import Clients
from sio_mvp.config import Settings
from sio_mvp.identities import conforming_number
from sio_mvp.journal import Journal
from sio_mvp.run_context import RunContext

MAX_IDENTITY_ATTEMPTS = 6
WORLD_FILE = "world.json"


@dataclass
class World:
    vars: dict[str, Any]
    runner: Runner

    def __getitem__(self, name: str) -> Any:
        return self.vars[name]

    def step(self, step_id: str):
        return catalogue.by_id()[step_id]

    def run(self, step_id: str, **kwargs):
        return self.runner.run(self.step(step_id), **kwargs)


def business_date(timezone: str | None) -> str:
    """Fecha de negocio en la zona horaria efectiva de la sucursal (no la del equipo de pruebas)."""
    return datetime.now(ZoneInfo(timezone or "America/Bogota")).date().isoformat()


def _identity(runner: Runner, step, variable: str, pattern: str, label: str) -> None:
    """Alta de identidad con un número conforme a la regla; si el número ya existe (409), otro intento."""
    for attempt in range(1, MAX_IDENTITY_ATTEMPTS + 1):
        number = conforming_number(pattern, runner.context, label, attempt)
        runner.vars[variable] = number
        runner.journal.protect(number)
        response = runner.run(step, expect={201, 409})
        if response.status == 201:
            return
    raise StepFailed(f"{step.id}: no se obtuvo un número de identificación libre en {MAX_IDENTITY_ATTEMPTS} intentos")


def build(runner: Runner) -> None:
    variables = runner.vars
    for step in catalogue.CONFIGURATION:
        if step.family in ("C-01", "C-02"):
            name = step.id.split(".", 1)[1]
            if step.family == "C-01":
                _identity(runner, step, f"nit_{name}", variables["patron_nit"], f"org-{name}")
            else:
                _identity(runner, step, f"cc_{name}", variables["patron_cc"], f"persona-{name}")
            continue
        runner.run(step)
        if step.id == "C-04.a1":
            variables["fecha_negocio"] = business_date(variables.get("zona_a1"))


def save(path: Path, variables: dict[str, Any]) -> None:
    public = {name: value for name, value in variables.items() if not is_protected(name)}
    path.write_text(json.dumps(public, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _protect_identities(runner: Runner) -> None:
    """Registra en el diario los números de identificación del mundo (leídos de Party Identity)."""
    admin = runner.clients.user("admin.test")
    for name in (org for org, _ in catalogue.ORGANIZATIONS):
        identity = runner.vars.get(f"org_{name}")
        if identity:
            response = admin.get("party-identity", f"/organization-identities/{identity}", step_id="mundo-protegidos")
            if response.status == 200:
                runner.journal.protect(response.body.get("identification_number"))
    for name in catalogue.PERSONS:
        identity = runner.vars.get(f"persona_{name}")
        if identity:
            response = admin.get("party-identity", f"/person-identities/{identity}", step_id="mundo-protegidos")
            if response.status == 200:
                runner.journal.protect(response.body.get("identification_number"))


def load_or_build(
    *, settings: Settings, context: RunContext, journal: Journal, clients: Clients, report_dir: Path
) -> World:
    path = Path(report_dir) / WORLD_FILE
    if path.is_file():
        runner = Runner(clients, context, journal, json.loads(path.read_text(encoding="utf-8")))
        _protect_identities(runner)
        return World(runner.vars, runner)
    runner = Runner(clients, context, journal, {})
    try:
        build(runner)
    finally:
        # Lo construido se conserva aunque un paso falle (los datos ya existen en los servicios).
        save(path, runner.vars)
    return World(runner.vars, runner)


def persist(world: World, report_dir: Path) -> None:
    save(Path(report_dir) / WORLD_FILE, world.vars)
