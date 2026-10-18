"""Rendimiento comparativo de las rutas por sucursal en la pila aislada (ampliación aditiva de la spec 022).

Para cada consulta mide, intercalando las solicitudes para que la carga del equipo afecte a todas por igual:

- la ruta de la empresa consolidada (`/companies/{c}/<consulta>`);
- la ruta de la empresa con un `branch_id` (`?branch_id=`);
- la ruta por sucursal (`/companies/{c}/branches/{b}/<consulta>`).

La ruta por sucursal debe cumplir el umbral de una sucursal (RNF-022-1: 1 s en los listados, 2 s en el resumen),
hacer las mismas llamadas internas que `?branch_id=` (del log del plan, FR-022-140) y no ser más lenta que ella
más un margen de ruido. Resultados en `$SIO_IT_STATE_DIR/performance-branch-<perfil>.json` (fuera del repositorio).
"""

from __future__ import annotations

import json
import statistics
import time

import pytest

from tests.integration.support import PIQ
from tests.performance.test_routes_performance import REPETITIONS, STATE, WARMUP, plan_of

pytestmark = pytest.mark.performance

THRESHOLDS = {"product-overviews": 1.0, "inventory-overviews": 1.0, "low-stock-products": 1.0,
              "inventory-summary": 2.0}
NOISE_SECONDS = 0.05
NOISE_RATIO = 1.25


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, int(round(0.95 * len(ordered))) - 1)]


@pytest.mark.parametrize("profile", ["dao", "sesgado"])
def test_branch_routes_against_company_routes(users, profile) -> None:
    path = STATE / f"synthetic-{profile}.json"
    if not path.is_file():
        pytest.skip(f"Siembre el perfil {profile} con validation/isolated-stack/synthetic.py")
    data = json.loads(path.read_text(encoding="utf-8"))
    company, branch = data["company"], data["branches"][0]
    client = users("supervisor.test")
    results, failures = [], []
    for endpoint, threshold in THRESHOLDS.items():
        variants = {
            "empresa consolidada": (f"{PIQ}/companies/{company}/{endpoint}", {}),
            "empresa ?branch_id": (f"{PIQ}/companies/{company}/{endpoint}", {"branch_id": branch}),
            "ruta por sucursal": (f"{PIQ}/companies/{company}/branches/{branch}/{endpoint}", {}),
        }
        durations = {name: [] for name in variants}
        traces, statuses = {}, {}
        for _ in range(WARMUP):
            for url, params in variants.values():
                client.get(url, params=params)
        for _ in range(REPETITIONS):
            for name, (url, params) in variants.items():
                started = time.perf_counter()
                response = client.get(url, params=params)
                durations[name].append(time.perf_counter() - started)
                statuses[name], traces[name] = response.status_code, response.headers.get("x-trace-id")
        rows = {
            name: {"p50_s": round(statistics.median(values), 3), "p95_s": round(p95(values), 3),
                   "estado": statuses[name],
                   "plan": plan_of(traces[name]) if endpoint != "inventory-summary" else None}
            for name, values in durations.items()
        }
        row = {"endpoint": endpoint, "umbral_s": threshold, **rows}
        results.append(row)
        by_path, by_query = rows["ruta por sucursal"], rows["empresa ?branch_id"]
        problems = []
        if any(item["estado"] != 200 for item in rows.values()):
            problems.append("estado distinto de 200")
        if by_path["p95_s"] > threshold:
            problems.append("p95 de la ruta por sucursal sobre el umbral")
        if by_path["p50_s"] > by_query["p50_s"] * NOISE_RATIO + NOISE_SECONDS:
            problems.append("la ruta por sucursal es más lenta que ?branch_id")
        if by_path["plan"] and by_query["plan"] and by_path["plan"]["calls"] != by_query["plan"]["calls"]:
            problems.append("llamadas internas distintas de ?branch_id")
        if problems:
            failures.append({**row, "problemas": problems})
    out = STATE / f"performance-branch-{profile}.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    assert not failures, json.dumps(failures, indent=2, ensure_ascii=False)
