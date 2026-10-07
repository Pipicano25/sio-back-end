"""Consultas de valoración, capas y consumos (rutas 29–31; FR-056; Historia 3 escenario 5; T025)."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import text

from tests.contract.db_rows import insert_layer
from tests.conftest import line, operation_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def base(world) -> str:
    return f"/api/v1/companies/{world.company}"


def apply(operator, world):
    a, b = world.products[0], world.products[1]
    for product, quantity, cost in ((a, "10", "1000"), (a, "5", "1300"), (b, "2", "50")):
        assert operator.post(ENTRIES, json=operation_body(world, line(product, quantity, unit_cost=cost))).status_code == 201
    sale = operator.post(OUTPUTS, json=operation_body(world, line(a, "12"), origin_type="SALE"))
    assert sale.status_code == 201
    return a, b, sale.json()


def test_branch_valuation(operator, world) -> None:
    a, b, _ = apply(operator, world)
    response = operator.get(f"{base(world)}/branches/{world.branch}/valuation")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total_value"] == "4000.00"  # 3 × 1 300 + 2 × 50
    assert data["has_unknown_cost"] is False
    assert (data["page"], data["page_size"], data["total_records"]) == (1, 20, 2)
    items = {item["company_product_id"]: item for item in data["items"]}
    assert items[str(a)] == {
        "company_product_id": str(a),
        "quantity": "3.0000",
        "inventory_value": "3900.00",
        "average_unit_cost": "1300.0000",
        "open_layers": 1,
        "has_unknown_cost": False,
    }
    assert items[str(b)]["open_layers"] == 1


def test_layers_in_fifo_order_with_and_without_closed_ones(operator, world) -> None:
    a, _, _ = apply(operator, world)
    url = f"{base(world)}/branches/{world.branch}/valuation/{a}/layers"
    open_only = operator.get(url).json()
    assert [(item["layer_kind"], item["remaining_quantity"], item["status"]) for item in open_only["items"]] == [
        ("ENTRY", "3.0000", "OPEN")
    ]
    everything = operator.get(url, params={"include_closed": "true"}).json()
    assert [(item["unit_cost"], item["original_quantity"], item["remaining_quantity"], item["status"]) for item in everything["items"]] == [
        ("1000.0000", "10.0000", "0.0000", "CLOSED"),
        ("1300.0000", "5.0000", "3.0000", "OPEN"),
    ]
    first = everything["items"][0]
    assert set(first) >= {"id", "layer_kind", "origin_movement_id", "cost_known", "currency_code", "received_at"}
    assert (first["cost_known"], first["currency_code"]) == (True, "COP")


def test_cost_consumptions_of_a_movement(operator, world) -> None:
    _, _, sale = apply(operator, world)
    movement = sale["movements"][0]["id"]
    response = operator.get(f"{base(world)}/inventory-movements/{movement}/cost-consumptions")
    assert response.status_code == 200
    data = response.json()
    assert data["movement_id"] == movement
    assert [
        (item["consumption_type"], item["quantity"], item["unit_cost"], item["cost_amount"], item["cost_known"], item["restores_consumption_id"])
        for item in data["items"]
    ] == [
        ("CONSUME", "10.0000", "1000.0000", "10000.00", True, None),
        ("CONSUME", "2.0000", "1300.0000", "2600.00", True, None),
    ]
    assert operator.get(f"{base(world)}/inventory-movements/{uuid4()}/cost-consumptions").status_code == 404


def test_unknown_cost_opening_is_explicit_and_distinct_from_a_real_zero(operator, world, test_engine) -> None:
    """Punto 2: "sin costo" se informa con `cost_known = false`; nunca se deduce de `unit_cost = 0`."""
    unknown, zero = world.products[0], world.products[1]
    with test_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO inventory_balances (company_id, branch_id, company_product_id, quantity, version, "
                "inventory_value, average_unit_cost, has_unknown_cost, created_by, updated_by) "
                "VALUES (:c, :b, :p, 4, 0, 0, 0, true, 's', 's')"
            ),
            {"c": world.company, "b": world.branch, "p": unknown},
        )
        insert_layer(
            connection, company_id=world.company, branch_id=world.branch, company_product_id=unknown,
            original_quantity=4, remaining_quantity=4, unit_cost=0, cost_known=False, currency_code=None,
        )
    assert operator.post(ENTRIES, json=operation_body(world, line(zero, "3", unit_cost="0"))).status_code == 201

    data = operator.get(f"{base(world)}/branches/{world.branch}/valuation").json()
    items = {item["company_product_id"]: item for item in data["items"]}
    assert (items[str(unknown)]["inventory_value"], items[str(unknown)]["has_unknown_cost"]) == ("0.00", True)
    assert (items[str(zero)]["inventory_value"], items[str(zero)]["has_unknown_cost"]) == ("0.00", False)
    assert data["has_unknown_cost"] is True

    layer_unknown = operator.get(f"{base(world)}/branches/{world.branch}/valuation/{unknown}/layers").json()["items"][0]
    layer_zero = operator.get(f"{base(world)}/branches/{world.branch}/valuation/{zero}/layers").json()["items"][0]
    assert (layer_unknown["unit_cost"], layer_unknown["cost_known"], layer_unknown["currency_code"]) == ("0.0000", False, None)
    assert (layer_zero["unit_cost"], layer_zero["cost_known"]) == ("0.0000", True)


def test_scope_and_permissions(operator, as_user, as_token, service_token, world, fake_oc) -> None:
    apply(operator, world)
    url = f"{base(world)}/branches/{world.branch}/valuation"
    assert as_user("inventario.test").get(url).status_code == 200
    for username in ("compras.test", "ventas.test", "reportes.test", "consulta.test"):
        assert as_user(username).get(url).status_code == 403

    other = f"/api/v1/companies/{world.other_company}/branches/{world.other_company_branch}/valuation"
    assert as_user("inventario.test").get(other).status_code == 404

    fake_oc.fail_if_called = True
    technical = as_token(service_token("perm:inventory:valuation:read", "perm:inventory:platform:lookup"))
    assert technical.get(url).status_code == 200


def test_other_company_branch_shows_nothing(operator, world) -> None:
    apply(operator, world)
    # La sucursal de otra empresa bajo la empresa propia: página vacía, sin revelar nada.
    response = operator.get(f"{base(world)}/branches/{world.other_company_branch}/valuation")
    assert response.status_code == 200
    assert (response.json()["items"], response.json()["total_value"]) == ([], "0.00")
