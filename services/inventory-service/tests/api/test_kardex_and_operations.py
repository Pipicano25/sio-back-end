"""Kardex y consulta de operaciones (Historia 5; FR-042, FR-043; T047)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from tests.conftest import line, operation_body, reversal_body

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"


def test_kardex_in_order_with_chained_balances(operator, as_user, world) -> None:
    product = world.products[0]
    entry = operator.post(ENTRIES, json=operation_body(world, line(product, "10", unit_cost="5"))).json()
    output = operator.post(OUTPUTS, json=operation_body(world, line(product, "3"), origin_type="SALE")).json()
    operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=reversal_body(world))

    response = as_user("inventario.test").get(
        f"/api/v1/companies/{world.company}/branches/{world.branch}/kardex/{product}"
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["movement_type"] for item in items] == ["PURCHASE_ENTRY", "SALE_OUTPUT", "OUTPUT_REVERSAL"]
    assert [item["balance_sequence"] for item in items] == [1, 2, 3]
    assert [(item["previous_balance"], item["new_balance"]) for item in items] == [
        ("0.0000", "10.0000"), ("10.0000", "7.0000"), ("7.0000", "10.0000")
    ]
    first = items[0]
    assert first["operation_id"] == entry["id"]
    assert (first["origin_type"], first["origin_id"], first["application_user_id"]) == ("PURCHASE", entry["origin_id"], str(world.user))
    assert first["unit_cost"] == "5.0000" and first["created_by"] and first["created_at"]
    assert items[2]["reversed_movement_id"] == items[1]["id"]
    assert items[2]["reason"] == reversal_body(world)["reason"]


def test_kardex_filters(operator, as_user, world) -> None:
    product = world.products[0]
    entry = operator.post(ENTRIES, json=operation_body(world, line(product, "10"))).json()
    operator.post(OUTPUTS, json=operation_body(world, line(product, "3"), origin_type="SALE"))
    url = f"/api/v1/companies/{world.company}/branches/{world.branch}/kardex/{product}"
    reader = as_user("inventario.test")

    assert [i["movement_type"] for i in reader.get(url, params={"movement_type": "SALE_OUTPUT"}).json()["items"]] == ["SALE_OUTPUT"]
    assert len(reader.get(url, params={"origin_type": "PURCHASE", "origin_id": entry["origin_id"]}).json()["items"]) == 1
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    assert reader.get(url, params={"occurred_at_from": future}).json()["items"] == []
    assert len(reader.get(url, params={"occurred_at_from": past, "occurred_at_to": future}).json()["items"]) == 2

    invalid = reader.get(url, params={"occurred_at_from": future, "occurred_at_to": past})
    assert invalid.status_code == 422 and invalid.json()["errors"][0]["code"] == "INVALID_DATE_RANGE"
    assert reader.get(url, params={"otro": "x"}).status_code == 422


def test_empty_kardex_is_an_empty_page(as_user, world) -> None:
    response = as_user("inventario.test").get(
        f"/api/v1/companies/{world.company}/branches/{world.branch}/kardex/{uuid4()}"
    )
    assert response.status_code == 200
    assert response.json()["items"] == [] and response.json()["total_records"] == 0


def test_operation_by_id_and_by_key(operator, as_user, world) -> None:
    product = world.products[0]
    body = operation_body(world, line(product, "2"))
    entry = operator.post(ENTRIES, json=body).json()
    reversal = operator.post(f"{ENTRIES}/{entry['id']}/reversal", json=reversal_body(world)).json()
    reader = as_user("inventario.test")
    base = f"/api/v1/companies/{world.company}/inventory-operations"

    by_id = reader.get(f"{base}/{entry['id']}")
    assert by_id.status_code == 200
    assert by_id.json()["reversed_by_operation_id"] == reversal["id"]
    assert by_id.json()["movements"][0]["id"] == entry["movements"][0]["id"]
    assert "balances" not in by_id.json()
    assert by_id.json()["reason"] is None and "reversed_by_operation_id" in by_id.json()

    by_key = reader.get(f"{base}/by-key/{body['operation_key']}")
    assert by_key.status_code == 200 and by_key.json()["id"] == entry["id"]


def test_operation_of_another_company_is_404(operator, as_user, world, fake_oc) -> None:
    entry = operator.post(ENTRIES, json=operation_body(world, line(world.products[0], "2"))).json()
    fake_oc.add_member("sub-inventario.test", world.other_company)
    reader = as_user("inventario.test")
    assert reader.get(f"/api/v1/companies/{world.other_company}/inventory-operations/{entry['id']}").status_code == 404
    assert reader.get(f"/api/v1/companies/{world.company}/inventory-operations/{uuid4()}").status_code == 404
    assert reader.get(f"/api/v1/companies/{world.company}/inventory-operations/by-key/{uuid4()}").status_code == 404
