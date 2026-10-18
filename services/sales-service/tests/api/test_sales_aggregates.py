"""Agregaciones de ventas para reportes (spec 023, SAL-R1 y SAL-R2).

Requieren la base de pruebas de Sales (`SALES_TEST_DATABASE_URL`). Por la estrategia aprobada de la spec 023 no
se crean bases temporales: estas pruebas se ejecutan cuando exista una base de pruebas aislada autorizada.

Cubren: presentaciones agrupadas en unidad base con el factor guardado, `DRAFT` y `CANCELLED` excluidas, orden
por cantidad (por defecto) o importe, totales por moneda de todo el alcance, filtro de sucursal, período máximo,
aislamiento entre empresas, permisos y ausencia de costos.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from tests.conftest import base, line, user_sub

TODAY = date.today()
PERIOD = {"date_from": (TODAY - timedelta(days=1)).isoformat(), "date_to": (TODAY + timedelta(days=1)).isoformat()}
COST_WORDS = ("cost", "margin", "unit_cost", "profit")


def by_product(client, world, **params):
    return client.get(f"{base(world)}/sales-aggregates/by-product", params={**PERIOD, **params})


def by_branch(client, world, **params):
    return client.get(f"{base(world)}/sales-aggregates/by-branch", params={**PERIOD, **params})


def seed(world, fakes, make_sequence, make_draft, confirm, cancel):
    """Venta 1: 2 cajas ×12 + 3 und del producto 1 y 1 und del producto 2 (confirmada).
    Venta 2: 5 und del producto 1 (confirmada y anulada). Venta 3: borrador de 7 und."""
    make_sequence()
    fakes.inventory.stock(world.branch, world.product, "100", "1000")
    fakes.inventory.stock(world.branch, world.product_2, "100", "6000")
    first = make_draft(
        line(world.product, "2", company_product_presentation_id=world.presentation),  # 2 × 18000 = 36000, 24 base
        line(world.product, "3"),  # 3 × 1500 = 4500
        line(world.product_2, "1"),  # 9000
    )
    assert confirm(first).status_code == 200
    second = make_draft(line(world.product, "5"))
    confirmed = confirm(second)
    assert confirmed.status_code == 200
    assert cancel(confirmed.json()).status_code == 200
    make_draft(line(world.product, "7"))


def test_groups_presentations_in_base_units_and_excludes_drafts_and_cancelled(supervisor, world, fakes, make_sequence,
                                                                               make_draft, confirm, cancel) -> None:
    seed(world, fakes, make_sequence, make_draft, confirm, cancel)
    response = by_product(supervisor, world, include_presentations="true")
    assert response.status_code == 200, response.text
    body = response.json()
    first, second = body["items"]
    assert first["company_product_id"] == str(world.product)
    assert (first["quantity_base"], first["amount"], first["sales_count"]) == ("27.0000", "40500.00", 1)
    assert {(p["quantity"], p["quantity_base"], p["amount"]) for p in first["presentations"]} == {
        ("2.0000", "24.0000", "36000.00"), ("3.0000", "3.0000", "4500.00")}
    assert (second["company_product_id"], second["quantity_base"], second["amount"]) == (
        str(world.product_2), "1.0000", "9000.00")
    assert body["totals"] == [{"currency_code": "COP", "amount": "49500.00", "sales_count": 1}]
    assert body["sales_status"] == "CONFIRMED" and body["order_by"] == "quantity_base"


def test_order_by_amount_and_limit(supervisor, world, fakes, make_sequence, make_draft, confirm, cancel) -> None:
    seed(world, fakes, make_sequence, make_draft, confirm, cancel)
    items = by_product(supervisor, world, order_by="amount", limit=1).json()["items"]
    assert [item["company_product_id"] for item in items] == [str(world.product)]
    assert "presentations" not in items[0] or items[0]["presentations"] is None


def test_branch_filter_and_by_branch(supervisor, world, fakes, make_sequence, make_draft, confirm, cancel) -> None:
    seed(world, fakes, make_sequence, make_draft, confirm, cancel)
    assert by_product(supervisor, world, branch_id=str(world.branch_b)).json()["items"] == []
    body = by_branch(supervisor, world).json()
    assert body["items"] == [{"branch_id": str(world.branch), "currency_code": "COP", "sales_count": 1,
                              "total_amount": "49500.00"}]
    assert body["totals"] == [{"currency_code": "COP", "sales_count": 1, "total_amount": "49500.00"}]
    assert by_branch(supervisor, world, branch_id=str(world.branch_b)).json()["items"] == []


def test_no_costs_even_with_profitability(supervisor, world, fakes, make_sequence, make_draft, confirm, cancel) -> None:
    seed(world, fakes, make_sequence, make_draft, confirm, cancel)
    for response in (by_product(supervisor, world, include_presentations="true"), by_branch(supervisor, world)):
        text = response.text.lower()
        assert not any(word in text for word in COST_WORDS), response.text


def test_period_validation(supervisor, world) -> None:
    long = {"date_from": "2025-01-01", "date_to": "2026-01-02"}  # 367 días
    assert supervisor.get(f"{base(world)}/sales-aggregates/by-product", params=long).status_code == 422
    reversed_ = {"date_from": "2026-02-01", "date_to": "2026-01-01"}
    assert supervisor.get(f"{base(world)}/sales-aggregates/by-branch", params=reversed_).status_code == 422
    assert supervisor.get(f"{base(world)}/sales-aggregates/by-branch").status_code == 422  # fechas obligatorias
    assert by_product(supervisor, world, limit=101).status_code == 422
    assert by_product(supervisor, world, desconocido="x").status_code == 422


def test_other_company_and_permissions(as_user, make_token, as_token, world, fakes, make_sequence, make_draft, confirm,
                                       cancel) -> None:
    seed(world, fakes, make_sequence, make_draft, confirm, cancel)
    fakes.oc.members.pop((user_sub("ventas.test"), world.company))
    assert by_product(as_user("ventas.test"), world).status_code == 404
    other = as_user("supervisor.test").get(f"/api/v1/companies/{world.other_company}/sales-aggregates/by-product",
                                            params=PERIOD)
    assert other.status_code == 404
    unrelated = as_token(make_token("perm:inventory:all:all", sub="sin-permiso-" + uuid4().hex))
    assert by_product(unrelated, world).status_code == 403
    assert by_branch(unrelated, world).status_code == 403
