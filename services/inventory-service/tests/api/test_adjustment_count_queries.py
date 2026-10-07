"""Consultas de ajustes y conteos (rutas 12–13 y 19–20; Historia 6, escenarios 1–3; SC-006; T050)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.conftest import ADJUSTMENTS_READ, COUNTS_READ, PLATFORM_LOOKUP, line, operation_body

ENTRIES = "/api/v1/inventory-entries"


def base(company) -> str:
    return f"/api/v1/companies/{company}"


def adjustment_body(world, product, kind="NEGATIVE", quantity="1", **extra):
    body = {
        "adjustment_key": str(uuid4()),
        "branch_id": str(world.branch),
        "company_product_id": str(product),
        "adjustment_type": kind,
        "quantity": quantity,
        "reason": "Ajuste ficticio",
    }
    body.update(extra)
    return body


@pytest.fixture
def data(operator, as_user, world):
    """Dos ajustes y un conteo completado en la empresa; un conteo en curso en otra sucursal."""
    clerk = as_user("inventario.test")
    a, b, _ = world.products
    assert operator.post(ENTRIES, json=operation_body(world, line(a, "10", unit_cost="5"), line(b, "10", unit_cost="7"))).status_code == 201
    first = clerk.post(f"{base(world.company)}/inventory-adjustments", json=adjustment_body(world, a)).json()
    second = clerk.post(
        f"{base(world.company)}/inventory-adjustments", json=adjustment_body(world, b, "POSITIVE", "2")
    ).json()
    count = clerk.post(f"{base(world.company)}/inventory-counts", json={"branch_id": str(world.branch)}).json()
    started = clerk.post(f"{base(world.company)}/inventory-counts/{count['id']}/start", json={"version": 1}).json()
    clerk.request("PUT", f"{base(world.company)}/inventory-counts/{count['id']}/details/{a}", json={"counted_quantity": "7"})
    completed = clerk.post(
        f"{base(world.company)}/inventory-counts/{count['id']}/complete",
        json={"completion_key": str(uuid4()), "version": started["version"]},
    ).json()
    return {"first": first, "second": second, "count": completed}


def test_get_adjustment_with_its_movement(as_user, world, data) -> None:
    """Historia 6 escenario 1."""
    response = as_user("inventario.test").get(f"{base(world.company)}/inventory-adjustments/{data['first']['id']}")
    assert response.status_code == 200
    assert response.json() == data["first"]


def test_list_adjustments_with_filters_and_order(as_user, world, data) -> None:
    client = as_user("inventario.test")
    url = f"{base(world.company)}/inventory-adjustments"
    everything = client.get(url).json()
    assert everything["total_records"] == 3
    assert [item["id"] for item in everything["items"]][1:] == [data["second"]["id"], data["first"]["id"]]
    by_type = client.get(url, params={"adjustment_type": "POSITIVE"}).json()
    assert [item["id"] for item in by_type["items"]] == [data["second"]["id"]]
    by_count = client.get(url, params={"inventory_count_id": data["count"]["id"]}).json()
    assert [item["inventory_count_id"] for item in by_count["items"]] == [data["count"]["id"]]
    by_product = client.get(url, params={"company_product_id": str(world.products[1])}).json()
    assert by_product["total_records"] == 1
    paged = client.get(url, params={"page_size": 1, "page": 2}).json()
    assert (len(paged["items"]), paged["total_pages"]) == (1, 3)
    assert client.get(url, params={"page_size": 101}).status_code == 422
    assert client.get(url, params={"created_at_from": "2030-01-01T00:00:00Z", "created_at_to": "2020-01-01T00:00:00Z"}).status_code == 422


def test_get_completed_count_with_details_and_adjustments(as_user, world, data) -> None:
    """Historia 6 escenario 3."""
    response = as_user("inventario.test").get(f"{base(world.company)}/inventory-counts/{data['count']['id']}")
    assert response.status_code == 200
    count = response.json()
    assert count["status"] == "COMPLETED"
    assert [detail["difference_quantity"] for detail in count["details"]] == ["-2.0000"]  # 10 − 1 (ajuste) = 9; contados 7
    assert [item["id"] for item in count["adjustments"]] == [count["details"][0]["inventory_adjustment_id"]]


def test_list_counts(as_user, world, data) -> None:
    client = as_user("inventario.test")
    url = f"{base(world.company)}/inventory-counts"
    page = client.get(url, params={"branch_id": str(world.branch), "status": "COMPLETED"}).json()
    assert [item["id"] for item in page["items"]] == [data["count"]["id"]]
    assert client.get(url, params={"status": "IN_PROGRESS"}).json()["total_records"] == 0


def test_other_company_and_permissions(as_user, as_token, service_token, world, fake_oc, data) -> None:
    """Historia 6 escenario 2 y SC-006."""
    adjustment = data["first"]["id"]
    count = data["count"]["id"]
    other = base(world.other_company)
    assert as_user("inventario.test").get(f"{other}/inventory-adjustments/{adjustment}").status_code == 404
    assert as_user("inventario.test").get(f"{other}/inventory-counts/{count}").status_code == 404
    assert as_user("inventario.test").get(f"{base(world.company)}/inventory-adjustments/{uuid4()}").status_code == 404

    for username in ("compras.test", "ventas.test", "reportes.test", "consulta.test"):
        client = as_user(username)
        assert client.get(f"{base(world.company)}/inventory-adjustments").status_code == 403
        assert client.get(f"{base(world.company)}/inventory-counts").status_code == 403

    fake_oc.fail_if_called = True
    technical = as_token(service_token(ADJUSTMENTS_READ, COUNTS_READ, PLATFORM_LOOKUP))
    assert technical.get(f"{base(world.company)}/inventory-adjustments/{adjustment}").status_code == 200
    assert technical.get(f"{base(world.company)}/inventory-counts/{count}").status_code == 200
    fake_oc.fail_if_called = False
    isolated = as_token(service_token(ADJUSTMENTS_READ, COUNTS_READ))
    assert isolated.get(f"{base(world.company)}/inventory-adjustments").status_code == 404
