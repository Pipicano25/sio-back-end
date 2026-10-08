"""Eventos de catálogos simples (feature 016; acciones PC 1–16 y 29–32; T056).

Eventos de plataforma (`company_id` nulo), uno por operación; un `PUT` idéntico no registra nada.
"""

from __future__ import annotations

import pytest

V = "/api/v1"
TECHNICAL = {"id", "version", "created_at", "created_by", "updated_at", "updated_by"}


def check(event: dict, action: str, entity_type: str, entity_id: str) -> None:
    assert event["action"] == action and event["entity_type"] == entity_type
    assert event["entity_id"] == entity_id and event["result"] == "SUCCESS"
    assert event["company_id"] is None and event["branch_id"] is None
    assert event["redacted_paths"] == []
    for side in ("previous_values", "new_values"):
        assert not set(event[side] or {}) & TECHNICAL


def lifecycle(api, outbox, clear_outbox, *, path, body, update, suffix, entity, changed) -> dict:
    clear_outbox()
    created = api.post(f"{V}/{path}", json=body)
    assert created.status_code == 201, created.text
    item = created.json()
    url = f"{V}/{path}/{item['id']}"
    updated = api.put(url, json={**update, "version": item["version"]})
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert api.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    create, update_event, deactivate, reactivate = outbox()
    check(create, f"CREATE_{suffix}", entity, item["id"])
    assert create["previous_values"] is None and create["new_values"]["code"] == item["code"]
    check(update_event, f"UPDATE_{suffix}", entity, item["id"])
    assert set(update_event["new_values"]) == set(changed)
    check(deactivate, f"DEACTIVATE_{suffix}", entity, item["id"])
    assert deactivate["previous_values"]["status"] == "ACTIVE" and deactivate["new_values"]["status"] == "INACTIVE"
    check(reactivate, f"REACTIVATE_{suffix}", entity, item["id"])
    return item


def test_unit_of_measure(api, outbox, clear_outbox) -> None:
    lifecycle(api, outbox, clear_outbox, path="units-of-measure",
              body={"code": "KG", "name": "Kilogramo", "symbol": "kg", "measurement_type": "MASS", "allows_decimals": True},
              update={"name": "Kilogramo masa", "symbol": "kg"}, suffix="UNIT_OF_MEASURE", entity="UnitOfMeasure",
              changed={"name"})


def test_packaging_type(api, outbox, clear_outbox) -> None:
    lifecycle(api, outbox, clear_outbox, path="packaging-types", body={"code": "BOX", "name": "Caja"},
              update={"name": "Caja de cartón", "description": None}, suffix="PACKAGING_TYPE", entity="PackagingType",
              changed={"name"})


def test_brand(api, outbox, clear_outbox) -> None:
    lifecycle(api, outbox, clear_outbox, path="brands", body={"code": "ACME", "name": "ACME S.A."},
              update={"name": "Acme", "description": "Marca"}, suffix="BRAND", entity="Brand",
              changed={"name", "description"})


def test_category(api, outbox, clear_outbox) -> None:
    lifecycle(api, outbox, clear_outbox, path="categories", body={"code": "GRANOS", "name": "Granos"},
              update={"name": "Granos y cereales", "description": None, "parent_category_id": None},
              suffix="CATEGORY", entity="Category", changed={"name"})


def test_product_group_type(api, outbox, clear_outbox) -> None:
    lifecycle(api, outbox, clear_outbox, path="group-types", body={"code": "LINEA", "name": "Línea", "allows_multiple": False},
              update={"name": "Línea comercial", "allows_multiple": False, "display_order": 0},
              suffix="PRODUCT_GROUP_TYPE", entity="ProductGroupType", changed={"name"})


@pytest.mark.parametrize("path", ["brands", "units-of-measure"])
def test_identical_update_records_nothing(api, outbox, clear_outbox, path) -> None:
    body = {"code": "UND", "name": "Unidad"} if path == "brands" else {
        "code": "KG", "name": "Kilogramo", "symbol": "kg", "measurement_type": "MASS", "allows_decimals": True}
    item = api.post(f"{V}/{path}", json=body).json()
    clear_outbox()
    update = {"name": item["name"], "description": item.get("description")} if path == "brands" else {
        "name": item["name"], "symbol": item["symbol"]}

    response = api.put(f"{V}/{path}/{item['id']}", json={**update, "version": item["version"]})

    assert response.status_code == 200
    assert outbox() == []
