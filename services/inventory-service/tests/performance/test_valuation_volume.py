"""Volumen de la valoración FIFO (SC-002, SC-007; T051). Ejecutar con `pytest -m performance`.

Carga 1 000 000 de movimientos valorizados y 100 000 capas abiertas (100 sucursales × 10
productos; 1 000 movimientos y 100 capas por saldo) y mide:

- una salida valorizada de 100 líneas que consume varias capas (p95 < 2 s);
- el valor de una sucursal (p95 < 1 s);
- la finalización de un conteo de 500 productos (p95 < 5 s).
"""

from __future__ import annotations

import statistics
import time
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from tests.conftest import line, operation_body, user_sub

pytestmark = pytest.mark.performance

BRANCHES = 100
PRODUCTS_PER_BRANCH = 10
MOVEMENTS_PER_BALANCE = 1000
LAYERS_PER_BALANCE = 100
SAMPLES = 20
COUNT_PRODUCTS = 500
COUNT_SAMPLES = 10


def _p95(durations: list[float]) -> float:
    return statistics.quantiles(durations, n=20)[18]


def _load(test_engine, company: UUID) -> list[str]:
    branches = [str(uuid4()) for _ in range(BRANCHES)]
    with test_engine.begin() as connection:
        connection.execute(text("CREATE TEMP TABLE perf_keys_013 (branch uuid, product uuid, operation uuid) ON COMMIT DROP"))
        connection.execute(
            text("INSERT INTO perf_keys_013 VALUES (CAST(:b AS uuid), gen_random_uuid(), gen_random_uuid())"),
            [{"b": branch} for branch in branches for _ in range(PRODUCTS_PER_BRANCH)],
        )
        connection.execute(
            text(
                "INSERT INTO inventory_operations (id, operation_key, requested_by_client, operation_type, company_id, "
                "branch_id, origin_type, origin_id, application_user_id, correlation_id, line_count, request_hash, created_by) "
                "SELECT operation, gen_random_uuid(), 'perf', 'ENTRY', :c, branch, 'PURCHASE', "
                "gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), 1, repeat('a', 64), 'perf' FROM perf_keys_013"
            ),
            {"c": company},
        )
        connection.execute(
            text(
                "INSERT INTO inventory_movements (operation_id, company_id, branch_id, company_product_id, movement_type, "
                "quantity, previous_balance, new_balance, balance_sequence, unit_cost, movement_value, cost_known, "
                "origin_type, origin_id, origin_detail_id, line_index, application_user_id, correlation_id, "
                "created_by, updated_by, created_at, updated_at) "
                "SELECT o.id, :c, k.branch, k.product, 'PURCHASE_ENTRY', 1, g - 1, g, g, 10, 10, true, 'PURCHASE', o.origin_id, "
                "gen_random_uuid(), g - 1, o.application_user_id, o.correlation_id, 'perf', 'perf', "
                "now() - (interval '1 second' * (2000 - g)), now() - (interval '1 second' * (2000 - g)) "
                "FROM perf_keys_013 k JOIN inventory_operations o ON o.id = k.operation "
                f"CROSS JOIN generate_series(1, {MOVEMENTS_PER_BALANCE}) g"
            ),
            {"c": company},
        )
        # 100 capas abiertas de 10 unidades por saldo (Σ = 1 000 = saldo), referidas a sus movimientos.
        connection.execute(
            text(
                "INSERT INTO inventory_cost_layers (company_id, branch_id, company_product_id, layer_kind, origin_movement_id, "
                "original_quantity, remaining_quantity, unit_cost, cost_known, currency_code, received_at, status, "
                "created_by, updated_by) "
                "SELECT :c, m.branch_id, m.company_product_id, 'ENTRY', m.id, 10, 10, 10 + (m.balance_sequence % 7), true, "
                "'COP', m.created_at, 'OPEN', 'perf', 'perf' FROM inventory_movements m "
                f"WHERE m.company_id = :c AND m.balance_sequence % {MOVEMENTS_PER_BALANCE // LAYERS_PER_BALANCE} = 0"
            ),
            {"c": company},
        )
        connection.execute(
            text(
                "INSERT INTO inventory_balances (company_id, branch_id, company_product_id, quantity, version, "
                "inventory_value, average_unit_cost, created_by, updated_by) "
                "SELECT :c, l.branch_id, l.company_product_id, sum(l.remaining_quantity), "
                f"{MOVEMENTS_PER_BALANCE}, sum(round(l.remaining_quantity * l.unit_cost, 2)), "
                "round(sum(round(l.remaining_quantity * l.unit_cost, 2)) / sum(l.remaining_quantity), 4), 'perf', 'perf' "
                "FROM inventory_cost_layers l WHERE l.company_id = :c GROUP BY l.branch_id, l.company_product_id"
            ),
            {"c": company},
        )
        for table in ("inventory_movements", "inventory_balances", "inventory_cost_layers"):
            connection.execute(text(f"ANALYZE {table}"))
    return branches


def test_valuation_at_volume(as_user, operator, world, fake_oc, test_engine) -> None:
    branches = _load(test_engine, world.company)
    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM inventory_movements")).scalar_one() >= 1_000_000
        assert connection.execute(text("SELECT count(*) FROM inventory_cost_layers WHERE status = 'OPEN'")).scalar_one() >= 100_000

    # Valor de una sucursal (SC-007).
    reader = as_user("inventario.test")
    durations = []
    for branch in branches[:SAMPLES]:
        started = time.perf_counter()
        response = reader.get(f"/api/v1/companies/{world.company}/branches/{branch}/valuation")
        durations.append(time.perf_counter() - started)
        assert response.status_code == 200
        assert response.json()["total_records"] == PRODUCTS_PER_BRANCH
    print(f"p95 valor de sucursal: {_p95(durations):.3f} s")
    assert _p95(durations) < 1.0, ("valor de sucursal", _p95(durations))

    # Salida valorizada de 100 líneas sobre productos con muchas capas (SC-007).
    for _ in range(10):
        lines = [line(world.products[i % 3], "1", unit_cost=str(10 + i % 5)) for i in range(100)]
        assert operator.post("/api/v1/inventory-entries", json=operation_body(world, *lines)).status_code == 201
    output_durations = []
    for _ in range(SAMPLES):
        lines = [line(world.products[i % 3], "0.5") for i in range(100)]
        started = time.perf_counter()
        response = operator.post("/api/v1/inventory-outputs", json=operation_body(world, *lines, origin_type="SALE"))
        output_durations.append(time.perf_counter() - started)
        assert response.status_code == 201, response.text[:200]
    print(f"p95 salida valorizada de 100 líneas: {_p95(output_durations):.3f} s")
    assert _p95(output_durations) < 2.0, ("salida de 100 líneas", _p95(output_durations))


def _count_branch(test_engine, fake_oc, company: UUID) -> UUID:
    """Sucursal con 500 saldos de 10 unidades (una capa cada uno) asignada a `inventario.test`."""
    branch = fake_oc.add_branch(company)
    fake_oc.assign(user_sub("inventario.test"), branch)
    with test_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO inventory_balances (company_id, branch_id, company_product_id, quantity, version, inventory_value, "
                "average_unit_cost, created_by, updated_by) "
                f"SELECT :c, :b, gen_random_uuid(), 10, 0, 50, 5, 'perf', 'perf' FROM generate_series(1, {COUNT_PRODUCTS})"
            ),
            {"c": company, "b": branch},
        )
        connection.execute(
            text(
                "INSERT INTO inventory_cost_layers (company_id, branch_id, company_product_id, layer_kind, original_quantity, "
                "remaining_quantity, unit_cost, cost_known, received_at, status, created_by, updated_by) "
                "SELECT company_id, branch_id, company_product_id, 'OPENING', 10, 10, 5, true, now(), 'OPEN', 'perf', 'perf' "
                "FROM inventory_balances WHERE branch_id = :b"
            ),
            {"b": branch},
        )
    return branch


def test_count_of_500_products_completes_within_five_seconds(as_user, world, fake_oc, test_engine) -> None:
    """SC-002: completar un conteo de 500 productos aplica todo o nada en < 5 s (p95)."""
    clerk = as_user("inventario.test")
    durations = []
    for _ in range(COUNT_SAMPLES):
        branch = _count_branch(test_engine, fake_oc, world.company)
        count = clerk.post(f"/api/v1/companies/{world.company}/inventory-counts", json={"branch_id": str(branch)}).json()
        started_count = clerk.post(f"/api/v1/companies/{world.company}/inventory-counts/{count['id']}/start", json={"version": 1}).json()
        with test_engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO inventory_count_details (inventory_count_id, company_product_id, system_quantity_snapshot, "
                    "counted_quantity, difference_quantity, counted_by_user_id, counted_at, created_by, updated_by) "
                    "SELECT :count, company_product_id, 10, 9, -1, gen_random_uuid(), now(), 'perf', 'perf' "
                    "FROM inventory_balances WHERE branch_id = :b"
                ),
                {"count": count["id"], "b": branch},
            )
        started = time.perf_counter()
        response = clerk.post(
            f"/api/v1/companies/{world.company}/inventory-counts/{count['id']}/complete",
            json={"completion_key": str(uuid4()), "version": started_count["version"]},
        )
        durations.append(time.perf_counter() - started)
        assert response.status_code == 200, response.text[:300]
        assert len(response.json()["adjustments"]) == COUNT_PRODUCTS
    print(f"p95 finalización de un conteo de 500 productos: {_p95(durations):.3f} s")
    assert _p95(durations) < 5.0, ("conteo de 500 productos", _p95(durations))
