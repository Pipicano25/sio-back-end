"""p50 y p95 por ruta en la pila aislada (T142; RNF-022-1, RNF-022-2, RNF-022-4, RNF-022-5, RNF-022-8; SC-022-1,
SC-022-10).

Usa los juegos de `validation/isolated-stack/synthetic.py` (`synthetic-dao.json` y `synthetic-sesgado.json` en
`$SIO_IT_STATE_DIR`). Cada consulta se calienta y se mide `REPETITIONS` veces; del log del plan del contenedor
(`Plan ejecutado …`, FR-022-140) se toman la ruta, los lotes, los candidatos examinados y las llamadas de la última
ejecución. Los resultados se escriben en `$SIO_IT_STATE_DIR/performance-<perfil>.json` (fuera del repositorio).
"""

from __future__ import annotations

import json
import os
import re
import statistics
import time
from pathlib import Path

import pytest

from tests.integration.support import PIQ, container_logs

pytestmark = pytest.mark.performance

STATE = Path(os.environ.get("SIO_IT_STATE_DIR", "/tmp/sio-it-state"))
REPETITIONS = int(os.environ.get("PIQ_PERF_REPETITIONS", "20"))
WARMUP = 3
PLAN = re.compile(r"trace_id=(?P<trace>\w+) Plan ejecutado endpoint=(?P<endpoint>\S+) ruta=(?P<route>\S+) "
                  r"lotes=(?P<batches>\d+) examinados=(?P<examined>\d+) validos=(?P<valid>\d+) entregados=(?P<items>\d+) "
                  r"llamadas=(?P<calls>\d+) duracion_ms=(?P<ms>\d+) parcial=(?P<partial>\w+)")


def cases(data: dict) -> list[tuple[str, str, dict, float]]:
    """(nombre, endpoint, parámetros, umbral en s). Umbrales de RNF-022-1; con varios lotes, 2,5 s (RNF-022-8)."""
    one = {"branch_id": data["branches"][0]}
    brands = data["brands"]
    return [
        ("sin filtros, una sucursal", "product-overviews", {**one}, 1.0),
        ("sin filtros, consolidado", "product-overviews", {}, 1.5),
        ("búsqueda por nombre", "product-overviews", {"search": "Sintético Crema", **one}, 1.0),
        ("búsqueda con imagen", "product-overviews", {"search": "Sintético", "has_image": "true", **one}, 2.5),
        ("marca pequeña (15)", "product-overviews", {"brand_id": brands["PEQUENA"], **one}, 2.5),
        ("marca grande", "product-overviews", {"brand_id": brands["GRANDE"], **one}, 1.0),
        ("categoría", "product-overviews", {"category_id": data["category"], **one}, 2.5),
        ("has_image=true", "product-overviews", {"has_image": "true", **one}, 2.5),
        ("has_image=false", "product-overviews", {"has_image": "false", **one}, 2.5),
        ("existencias IN_STOCK", "product-overviews", {"stock_state": "IN_STOCK", **one}, 2.5),
        ("existencias OUT_OF_STOCK", "product-overviews", {"stock_state": "OUT_OF_STOCK", **one}, 2.5),
        ("combinado marca+imagen+existencias", "product-overviews",
         {"brand_id": brands["GRANDE"], "has_image": "true", "stock_state": "IN_STOCK", **one}, 2.5),
        ("orden explícito con marca (R-F)", "product-overviews",
         {"brand_id": brands["PEQUENA"], "sort": "display_name", **one}, 2.5),
        ("inventario, una sucursal", "inventory-overviews", {**one}, 1.0),
        ("inventario, consolidado", "inventory-overviews", {}, 1.5),
        ("bajo mínimo", "low-stock-products", {}, 1.0),
        ("resumen", "inventory-summary", {}, 2.0),
    ]


def plan_of(trace: str) -> dict | None:
    for line in reversed(container_logs("sio-it-product-inventory-query-service", "5m").splitlines()):
        match = PLAN.search(line)
        if match and match["trace"] == trace:
            return {key: match[key] for key in ("route", "batches", "examined", "valid", "items", "calls", "partial")}
    return None


@pytest.mark.parametrize("profile", ["dao", "sesgado"])
def test_routes(users, profile) -> None:
    path = STATE / f"synthetic-{profile}.json"
    if not path.is_file():
        pytest.skip(f"Siembre el perfil {profile} con validation/isolated-stack/synthetic.py")
    data = json.loads(path.read_text(encoding="utf-8"))
    client = users("supervisor.test")
    results, failures = [], []
    for name, endpoint, params, threshold in cases(data):
        url = f"{PIQ}/companies/{data['company']}/{endpoint}"
        for _ in range(WARMUP):
            client.get(url, params=params)
        durations, status, trace = [], None, None
        for _ in range(REPETITIONS):
            started = time.perf_counter()
            response = client.get(url, params=params)
            durations.append(time.perf_counter() - started)
            status, trace = response.status_code, response.headers.get("x-trace-id")
        durations.sort()
        p95 = durations[max(0, int(round(0.95 * len(durations))) - 1)]
        row = {"caso": name, "endpoint": endpoint, "estado": status, "p50_s": round(statistics.median(durations), 3),
               "p95_s": round(p95, 3), "umbral_s": threshold, "plan": plan_of(trace) if endpoint != "inventory-summary" else None}
        results.append(row)
        if status != 200 or p95 > threshold:
            failures.append(row)
    (STATE / f"performance-{profile}.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    assert not failures, json.dumps(failures, indent=2, ensure_ascii=False)
