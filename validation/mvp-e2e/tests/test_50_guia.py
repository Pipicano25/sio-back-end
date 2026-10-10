"""Etapa `guia`: la guía `docs/validacion-mvp/` es la generada desde los pasos y todos sus pasos se
ejecutaron contra los servicios en esta corrida (FR-020a, SC-009; research R-12).

Regenerar la guía: `SIO_MVP_GUIDE_WRITE=1 bash validation/mvp-e2e/run.sh --etapa recorrido --etapa
seguridad --etapa guia`.
"""

from __future__ import annotations

import json

import pytest

from scenario import steps as catalogue
from sio_mvp import guide

pytestmark = pytest.mark.e2e


@pytest.fixture(scope="module")
def generated(realm):
    return guide.render(catalogue.all_steps(), realm)


def test_versioned_guide_equals_generated(generated, settings):
    if settings.guide_write:
        guide.write(generated)
    versioned = guide.read()
    different = sorted(path for path in set(generated) | set(versioned) if generated.get(path) != versioned.get(path))
    assert not different, (
        "La guía versionada no es la generada; regenere con SIO_MVP_GUIDE_WRITE=1. Archivos distintos: " + ", ".join(different[:20])
    )


def test_every_guide_step_was_executed_in_this_run(report_dir):
    path = report_dir / "steps.jsonl"
    assert path.is_file(), "No hay diario de pasos en esta corrida: ejecute las etapas recorrido y seguridad antes de guia"
    executed: dict[str, set[int]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if "status" in entry and entry.get("step_id"):
            executed.setdefault(entry["step_id"], set()).add(entry["status"])
    missing = [step.id for step in catalogue.all_steps() if step.expect not in executed.get(step.id, set())]
    assert not missing, f"Pasos de la guía sin ejecutar (o con otro estado) en esta corrida: {missing}"


def test_every_permission_exists_in_realm_template(realm):
    unknown = sorted(
        {permission for step in catalogue.all_steps() for permission in guide.permissions(step) if not realm.permission_exists(permission)}
    )
    assert not unknown, f"Permisos citados que no concede ningún rol de la plantilla del realm: {unknown}"
