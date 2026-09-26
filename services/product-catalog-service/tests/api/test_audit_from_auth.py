"""La auditoría sale siempre del contexto de autenticación (RC-11, Principio VI)."""

import pytest

from tests import factories

CREATIONS = [
    ("/api/v1/units-of-measure", {"code": "KG", "name": "Kilo", "symbol": "kg", "measurement_type": "MASS", "allows_decimals": True}),
    ("/api/v1/packaging-types", {"code": "BOX", "name": "Caja"}),
    ("/api/v1/brands", {"code": "ACME", "name": "Acme"}),
    ("/api/v1/categories", {"code": "ALIMENTOS", "name": "Alimentos"}),
    ("/api/v1/attribute-definitions", {"code": "COLOR", "name": "Color", "description": "d", "data_type": "OPTION"}),
    ("/api/v1/group-types", {"code": "GROUP_1", "name": "Grupo 1"}),
]


@pytest.mark.parametrize(("url", "body"), CREATIONS)
def test_created_by_and_updated_by_come_from_token(api_as, url: str, body: dict) -> None:
    creator = api_as("perm:product-catalog:all:all", sub="creator-sub")
    editor = api_as("perm:product-catalog:all:all", sub="editor-sub")

    created = creator.post(url, json=body)
    assert created.status_code == 201, created.text
    assert created.json()["created_by"] == "creator-sub"
    assert created.json()["updated_by"] == "creator-sub"

    deactivated = editor.post(f"{url}/{created.json()['id']}/deactivate", json={"version": 1}).json()
    assert deactivated["created_by"] == "creator-sub"
    assert deactivated["updated_by"] == "editor-sub"
    assert deactivated["updated_at"] >= created.json()["updated_at"]


@pytest.mark.parametrize(("url", "body"), CREATIONS)
@pytest.mark.parametrize("field", ["created_by", "updated_by", "created_at", "version"])
def test_body_cannot_set_audit_fields(api, url: str, body: dict, field: str) -> None:
    response = api.post(url, json={**body, field: "x"})
    assert response.status_code == 422


def test_product_update_keeps_creator(api_as, session_factory) -> None:
    unit = factories.unit(session_factory)
    creator = api_as("perm:product-catalog:all:all", sub="creator-sub")
    editor = api_as("perm:product-catalog:all:all", sub="editor-sub")
    product = creator.post(
        "/api/v1/products",
        json={"product_type": "GOOD", "canonical_name": "Arroz", "base_unit_id": str(unit.id)},
    ).json()

    updated = editor.put(
        f"/api/v1/products/{product['id']}",
        json={"canonical_name": "Arroz blanco", "base_unit_id": str(unit.id), "version": 1},
    ).json()

    assert updated["created_by"] == "creator-sub"
    assert updated["updated_by"] == "editor-sub"
