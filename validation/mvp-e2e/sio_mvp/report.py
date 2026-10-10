"""Informe de la corrida: `summary.json`, `summary.md`, `timings.json` y códigos de salida.

Formato: `specs/017-mvp-integral-validation/contracts/evidence-format.md`; mapa de ítems:
`contracts/e2e-scenarios.md` §6; códigos de salida: `contracts/runner-cli.md` §3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

RESULTS = ("CUMPLE", "NO CUMPLE", "BLOQUEADO", "NO EJECUTADO")
STAGES = ("preflight", "recorrido", "seguridad", "caidas", "guia", "regresion")
STAGE_RESULTS = ("CUMPLE", "NO CUMPLE", "BLOQUEADA", "NO EJECUTADA")


@dataclass(frozen=True)
class Item:
    number: int
    roadmap: str
    scenarios: tuple[str, ...]
    steps: tuple[str, ...]
    stage: str


ITEMS: tuple[Item, ...] = (
    Item(1, "Crear empresa", ("H1-E1",), ("C-01", "C-03"), "recorrido"),
    Item(2, "Crear sucursal", ("H1-E1",), ("C-04",), "recorrido"),
    Item(3, "Crear usuario", ("H1-E1",), ("C-02", "C-05", "C-06", "C-07"), "recorrido"),
    Item(4, "Crear proveedor", ("H1-E2",), ("C-08",), "recorrido"),
    Item(5, "Crear cliente", ("H1-E2",), ("C-09",), "recorrido"),
    Item(6, "Crear/adoptar producto", ("H1-E2",), ("C-10", "C-11"), "recorrido"),
    Item(7, "Configurar presentación", ("H1-E2",), ("C-10", "C-11"), "recorrido"),
    Item(8, "Configurar precio", ("H1-E2",), ("C-11", "C-12"), "recorrido"),
    Item(9, "Registrar compra", ("H1-E3",), ("P-01",), "recorrido"),
    Item(10, "Confirmar compra", ("H1-E3",), ("P-02",), "recorrido"),
    Item(11, "Verificar entrada de inventario", ("H1-E3",), ("P-03",), "recorrido"),
    Item(12, "Verificar saldo", ("H1-E3",), ("P-03",), "recorrido"),
    Item(13, "Registrar venta", ("H1-E4", "H1-E6"), ("V-01",), "recorrido"),
    Item(14, "Validar stock", ("H1-E7",), ("V-02", "V-04"), "recorrido"),
    Item(15, "Confirmar venta", ("H1-E4", "H1-E6"), ("V-03", "V-05", "V-05b"), "recorrido"),
    Item(16, "Verificar salida de inventario", ("H1-E4",), ("V-06", "V-07"), "recorrido"),
    Item(17, "Verificar saldo final", ("H1-E5",), ("V-07", "A-03"), "recorrido"),
    Item(18, "Consultar kardex", ("H1-E5",), ("P-03", "V-07", "A-03"), "recorrido"),
    Item(19, "Verificar auditoría", ("H2",), ("U-01", "U-02"), "recorrido"),
    Item(20, "Probar anulaciones/reversos", ("H3",), ("A-01", "A-02", "A-03"), "recorrido"),
    Item(21, "Probar seguridad entre empresas", ("H4",), ("§3", "§4"), "seguridad"),
    Item(22, "Probar dependencia externa no disponible", ("H5",), ("O1", "O2", "O3", "O4a", "O4b", "O5", "O6"), "caidas"),
    Item(23, "Ejecutar pruebas completas del MVP", ("H6",), ("regresion",), "regresion"),
)


def _item_entry(item: Item, value: Any) -> dict:
    if value is None:
        detail: dict = {"result": "NO EJECUTADO"}
    elif isinstance(value, str):
        detail = {"result": value}
    else:
        detail = dict(value)
    result = detail.get("result")
    if result not in RESULTS:
        raise ValueError(f"Resultado inválido para el ítem {item.number}: {result!r}")
    return {
        "item": item.number,
        "roadmap": item.roadmap,
        "scenarios": list(item.scenarios),
        "tests": list(detail.get("tests", [])),
        "steps": list(item.steps),
        "evidence": list(detail.get("evidence", [])),
        "result": result,
    }


def blocking_gaps_open(gaps: list[Mapping]) -> bool:
    return any(
        gap.get("classification") == "BLOQUEANTE" and gap.get("status", "ABIERTA") != "CERRADA" for gap in gaps
    )


def gate_eligible(
    *, todo: bool, stages: Mapping[str, str], items: list[dict], environment_restored: bool, gaps: list[Mapping]
) -> bool:
    """P-07 y evidence-format.md §1: `--todo`, 6 etapas y 23 ítems en CUMPLE, entorno restaurado y sin
    brechas bloqueantes abiertas."""
    return (
        todo
        and all(stages.get(stage) == "CUMPLE" for stage in STAGES)
        and len(items) == len(ITEMS)
        and all(item["result"] == "CUMPLE" for item in items)
        and environment_restored
        and not blocking_gaps_open(gaps)
    )


def build_summary(
    *,
    run_id: str,
    started_at: str,
    finished_at: str,
    git_head: str,
    todo: bool,
    stages: Mapping[str, str],
    item_results: Mapping[int, Any],
    gaps: list[Mapping],
    environment_restored: bool,
    timings: Mapping[str, float],
    restored_containers: list[str] | None = None,
    unrestored_containers: list[str] | None = None,
) -> dict:
    for stage, result in stages.items():
        if result not in STAGE_RESULTS:
            raise ValueError(f"Resultado inválido para la etapa {stage}: {result!r}")
    items = [_item_entry(item, item_results.get(item.number)) for item in ITEMS]
    all_stages = {stage: stages.get(stage, "NO EJECUTADA") for stage in STAGES}
    return {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "git_head": git_head,
        "todo": todo,
        "stages": all_stages,
        "items": items,
        "gaps": list(gaps),
        "environment_restored": environment_restored,
        "restored_containers": list(restored_containers or []),
        "unrestored_containers": list(unrestored_containers or []),
        "gate_eligible": gate_eligible(
            todo=todo, stages=all_stages, items=items, environment_restored=environment_restored, gaps=list(gaps)
        ),
        "timings_seconds": dict(timings),
    }


def _cell(values: list[str]) -> str:
    return "<br>".join(f"`{value}`" for value in values) if values else "—"


def render_markdown(data: dict) -> str:
    lines = [
        f"# Validación integral del MVP — corrida {data['run_id']}",
        "",
        f"- Inicio: {data['started_at']} · Fin: {data['finished_at']} · `git HEAD`: `{data['git_head']}`",
        f"- Lanzada con `--todo`: {'sí' if data.get('todo') else 'no'}",
        f"- Entorno restaurado: {'sí' if data['environment_restored'] else 'NO'}",
        f"- **gate_eligible**: `{str(data['gate_eligible']).lower()}`",
        "",
        "## Etapas",
        "",
        "| Etapa | Resultado | Tiempo (s) |",
        "| --- | --- | --- |",
    ]
    timings = data.get("timings_seconds", {})
    for stage, result in data["stages"].items():
        seconds = timings.get(stage)
        lines.append(f"| {stage} | {result} | {seconds:.1f} |" if seconds is not None else f"| {stage} | {result} | — |")
    lines += [
        "",
        "## Ítems de la FASE 10",
        "",
        "| Ítem | Roadmap | Escenario | Prueba | Evidencia | Resultado |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in data["items"]:
        lines.append(
            f"| {item['item']} | {item['roadmap']} | {', '.join(item['scenarios'])} | {_cell(item['tests'])} | "
            f"{_cell(item['evidence'] or item['steps'])} | {item['result']} |"
        )
    lines += ["", "## Brechas", ""]
    if data["gaps"]:
        lines += ["| Id | Clasificación | Estado | Descripción |", "| --- | --- | --- | --- |"]
        for gap in data["gaps"]:
            lines.append(
                f"| {gap.get('id')} | {gap.get('classification')} | {gap.get('status', 'ABIERTA')} | {gap.get('description', '')} |"
            )
    else:
        lines.append("Sin brechas registradas en esta corrida.")
    lines += ["", "## Tiempos (informativos)", "", "| Etapa o macroetapa | Segundos |", "| --- | --- |"]
    for name, seconds in timings.items():
        lines.append(f"| {name} | {seconds:.1f} |")
    lines += ["", "## Contenedores", ""]
    lines.append(f"- Restaurados al final: {', '.join(data.get('restored_containers') or []) or 'ninguno'}")
    lines.append(f"- Sin restaurar: {', '.join(data.get('unrestored_containers') or []) or 'ninguno'}")
    return "\n".join(lines) + "\n"


def write(directory: Path, data: dict) -> None:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "summary.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (directory / "timings.json").write_text(
        json.dumps(data["timings_seconds"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (directory / "summary.md").write_text(render_markdown(data), encoding="utf-8")


def exit_code(*, preflight_ok: bool, stages: Mapping[str, str], environment_restored: bool) -> int:
    if not environment_restored:
        return 3
    if not preflight_ok:
        return 2
    if any(result in ("NO CUMPLE", "BLOQUEADA") for result in stages.values()):
        return 1
    return 0
