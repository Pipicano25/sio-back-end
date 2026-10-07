"""Volumen y tiempos de respuesta (SC-007; T049). Ejecutar con `pytest -m performance`.

Carga 1 000 000 de movimientos (1 000 saldos de empresas, sucursales y productos
distintos, 1 000 movimientos por saldo) con `INSERT … SELECT generate_series`, y mide la consulta de
saldo, la primera página del kardex y del stock (p95 < 1 s) y una operación de
100 líneas con dobles (p95 < 2 s).
"""

from __future__ import annotations

import statistics
import time
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from tests.conftest import line, operation_body

pytestmark = pytest.mark.performance

BALANCES = 1000
MOVEMENTS_PER_BALANCE = 1000
SAMPLES = 20


def _p95(durations: list[float]) -> float:
    return statistics.quantiles(durations, n=20)[18]


def _load(test_engine) -> list[tuple[str, str, str]]:
    keys = [
        (str(uuid4()), str(uuid4()), str(uuid4()))
        for _ in range(BALANCES)
    ]
    with test_engine.begin() as connection:
        connection.execute(text("CREATE TEMP TABLE perf_keys (company uuid, branch uuid, product uuid, n int)"))
        connection.execute(
            text("INSERT INTO perf_keys VALUES (CAST(:c AS uuid), CAST(:b AS uuid), CAST(:p AS uuid), :n)"),
            [{"c": c, "b": b, "p": p, "n": i} for i, (c, b, p) in enumerate(keys)],
        )
        connection.execute(
            text(
                "INSERT INTO inventory_operations (id, operation_key, requested_by_client, operation_type, company_id, "
                "branch_id, origin_type, origin_id, application_user_id, correlation_id, line_count, request_hash, created_by) "
                "SELECT gen_random_uuid(), gen_random_uuid(), 'perf', 'ENTRY', company, branch, 'PURCHASE', "
                "gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 1, repeat('a', 64), 'perf' FROM perf_keys"
            )
        )
        connection.execute(
            text(
                "INSERT INTO inventory_movements (operation_id, company_id, branch_id, company_product_id, movement_type, "
                "quantity, previous_balance, new_balance, balance_sequence, unit_cost, movement_value, cost_known, "
                "origin_type, origin_id, origin_detail_id, "
                "line_index, application_user_id, correlation_id, created_by, updated_by, created_at, updated_at) "
                # 013: todo movimiento nuevo es valorizado (`ck_inventory_movements_valued`).
                "SELECT o.id, k.company, k.branch, k.product, 'PURCHASE_ENTRY', 1, g - 1, g, g, 1, 1, true, 'PURCHASE', o.origin_id, "
                "gen_random_uuid(), g - 1, o.application_user_id, o.correlation_id, 'perf', 'perf', "
                "now() - (interval '1 second' * (2000 - g)), now() - (interval '1 second' * (2000 - g)) "
                f"FROM perf_keys k JOIN inventory_operations o ON o.company_id = k.company AND o.branch_id = k.branch "
                f"CROSS JOIN generate_series(1, {MOVEMENTS_PER_BALANCE}) g"
            )
        )
        connection.execute(
            text(
                "INSERT INTO inventory_balances (company_id, branch_id, company_product_id, quantity, version, created_by, updated_by) "
                f"SELECT company, branch, product, {MOVEMENTS_PER_BALANCE}, {MOVEMENTS_PER_BALANCE}, 'perf', 'perf' FROM perf_keys"
            )
        )
        connection.execute(text("ANALYZE inventory_movements"))
        connection.execute(text("ANALYZE inventory_balances"))
    return keys


def test_queries_and_operation_p95(as_user, operator, world, fake_oc, test_engine) -> None:
    keys = _load(test_engine)
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM inventory_movements")).scalar_one() >= 1_000_000

    reader = as_user("inventario.test")
    durations: dict[str, list[float]] = {"balance": [], "kardex": [], "stock": []}

    for company, branch, product in keys[:SAMPLES]:
        fake_oc.add_member("sub-inventario.test", UUID(company))
        base = f"/api/v1/companies/{company}/branches/{branch}"
        for name, url in (("balance", f"{base}/balances/{product}"), ("kardex", f"{base}/kardex/{product}"), ("stock", f"{base}/balances")):
            started = time.perf_counter()
            response = reader.get(url)
            durations[name].append(time.perf_counter() - started)
            assert response.status_code == 200

    for name, values in durations.items():
        assert _p95(values) < 1.0, (name, _p95(values))

    operation_durations = []
    for _ in range(SAMPLES):
        lines = [line(world.products[i % 3], "1") for i in range(100)]
        started = time.perf_counter()
        response = operator.post("/api/v1/inventory-entries", json=operation_body(world, *lines))
        operation_durations.append(time.perf_counter() - started)
        assert response.status_code == 201
    assert _p95(operation_durations) < 2.0, _p95(operation_durations)
