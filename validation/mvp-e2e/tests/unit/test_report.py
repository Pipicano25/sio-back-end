"""T010 — Informe, elegibilidad del gate y códigos de salida (sio_mvp.report)."""

import json

import pytest

from sio_mvp import report

pytestmark = pytest.mark.unit

ALL_STAGES = ("preflight", "recorrido", "seguridad", "caidas", "guia", "regresion")


def all_items(result="CUMPLE"):
    return {number: result for number in range(1, 24)}


def summary(**overrides):
    arguments = dict(
        run_id="A1B2C3D4",
        started_at="2026-10-09T14:00:00Z",
        finished_at="2026-10-09T16:00:00Z",
        git_head="abc123",
        todo=True,
        stages={stage: "CUMPLE" for stage in ALL_STAGES},
        item_results=all_items(),
        gaps=[],
        environment_restored=True,
        timings={"total": 10.0, "preflight": 1.0},
    )
    arguments.update(overrides)
    return report.build_summary(**arguments)


def test_item_map_has_the_23_items_of_phase_10():
    assert [item.number for item in report.ITEMS] == list(range(1, 24))
    assert report.ITEMS[9].roadmap == "Confirmar compra"
    assert report.ITEMS[21].steps == ("O1", "O2", "O3", "O4a", "O4b", "O5", "O6")
    assert report.ITEMS[22].stage == "regresion"


def test_summary_json_follows_evidence_format():
    data = summary()
    assert set(data) >= {
        "run_id",
        "started_at",
        "finished_at",
        "git_head",
        "stages",
        "items",
        "gaps",
        "environment_restored",
        "gate_eligible",
        "timings_seconds",
    }
    assert len(data["items"]) == 23
    first = data["items"][0]
    assert set(first) >= {"item", "roadmap", "scenarios", "tests", "steps", "evidence", "result"}
    assert {item["result"] for item in data["items"]} == {"CUMPLE"}


def test_missing_item_results_are_not_executed():
    data = summary(item_results={1: "CUMPLE"}, todo=False)
    results = {item["item"]: item["result"] for item in data["items"]}
    assert results[1] == "CUMPLE"
    assert results[2] == "NO EJECUTADO"


def test_invalid_result_is_rejected():
    with pytest.raises(ValueError):
        summary(item_results={**all_items(), 5: "OK"})


def test_gate_eligible_only_when_every_condition_holds():
    assert summary()["gate_eligible"] is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"todo": False},
        {"stages": {**{stage: "CUMPLE" for stage in ALL_STAGES}, "regresion": "NO EJECUTADA"}},
        {"stages": {stage: "CUMPLE" for stage in ALL_STAGES if stage != "guia"}},
        {"stages": {**{stage: "CUMPLE" for stage in ALL_STAGES}, "caidas": "NO CUMPLE"}},
        {"item_results": {**all_items(), 22: "BLOQUEADO"}},
        {"item_results": {**all_items(), 23: "NO EJECUTADO"}},
        {"environment_restored": False},
        {"gaps": [{"id": "G-017-01", "classification": "BLOQUEANTE", "status": "ABIERTA"}]},
    ],
)
def test_gate_not_eligible_when_a_condition_fails(overrides):
    assert summary(**overrides)["gate_eligible"] is False


def test_non_blocking_or_closed_gaps_do_not_prevent_the_gate():
    gaps = [
        {"id": "G-017-01", "classification": "NO BLOQUEANTE", "status": "ABIERTA"},
        {"id": "G-017-02", "classification": "BLOQUEANTE", "status": "CERRADA"},
    ]
    assert summary(gaps=gaps)["gate_eligible"] is True


def test_write_creates_summary_json_md_and_timings(tmp_path):
    data = summary()
    report.write(tmp_path, data)
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8")) == data
    assert json.loads((tmp_path / "timings.json").read_text(encoding="utf-8")) == data["timings_seconds"]
    markdown = (tmp_path / "summary.md").read_text(encoding="utf-8")
    assert "| Ítem | Roadmap | Escenario | Prueba | Evidencia | Resultado |" in markdown
    assert "Confirmar compra" in markdown
    assert "gate_eligible" in markdown


def test_exit_codes():
    assert report.exit_code(preflight_ok=True, stages={"recorrido": "CUMPLE"}, environment_restored=True) == 0
    assert report.exit_code(preflight_ok=True, stages={"recorrido": "NO CUMPLE"}, environment_restored=True) == 1
    assert report.exit_code(preflight_ok=True, stages={"recorrido": "BLOQUEADA"}, environment_restored=True) == 1
    assert report.exit_code(preflight_ok=False, stages={"preflight": "NO CUMPLE"}, environment_restored=True) == 2
    assert report.exit_code(preflight_ok=True, stages={"recorrido": "CUMPLE"}, environment_restored=False) == 3
    assert report.exit_code(preflight_ok=False, stages={}, environment_restored=False) == 3
