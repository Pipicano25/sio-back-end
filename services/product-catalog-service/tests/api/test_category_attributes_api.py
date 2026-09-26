"""Atributos por categoría y atributos aplicables (FR-041 a FR-043, DS-02, RN-15)."""

from tests import factories


def _url(category_id) -> str:
    return f"/api/v1/categories/{category_id}/attributes"


def test_associate_and_reactivate_pair(api, session_factory) -> None:
    category = factories.category(session_factory, "LECHES")
    fat = factories.definition(session_factory, "PORCENTAJE_GRASA")
    body = {"attribute_definition_id": str(fat.id), "is_required": True, "is_filterable": True, "display_order": 1}

    created = api.post(_url(category.id), json=body)
    assert created.status_code == 201
    association = created.json()

    duplicate = api.post(_url(category.id), json=body)
    assert duplicate.json()["code"] == "PRODUCT_CATALOG.DUPLICATE_ASSOCIATION"

    api.post(f"{_url(category.id)}/{association['id']}/deactivate", json={"version": 1})
    again = api.post(_url(category.id), json={**body, "is_required": False})
    assert again.status_code == 200
    assert again.json()["id"] == association["id"]
    assert again.json()["is_required"] is False


def test_inactive_references_rejected(api, session_factory) -> None:
    category = factories.category(session_factory, "LECHES", status="INACTIVE")
    active = factories.category(session_factory, "QUESOS")
    old = factories.definition(session_factory, "VIEJO", status="INACTIVE")
    fat = factories.definition(session_factory, "GRASA")

    first = api.post(_url(category.id), json={"attribute_definition_id": str(fat.id)})
    second = api.post(_url(active.id), json={"attribute_definition_id": str(old.id)})

    assert first.json()["code"] == "PRODUCT_CATALOG.REFERENCE_INACTIVE"
    assert second.json()["code"] == "PRODUCT_CATALOG.REFERENCE_INACTIVE"


def test_required_change_affects_completeness_only(api, session_factory) -> None:
    product, category, _ = factories.complete_product(session_factory)
    fat = factories.definition(session_factory, "GRASA")
    association = api.post(
        _url(category.id),
        json={"attribute_definition_id": str(fat.id), "is_required": False},
    ).json()
    assert api.get(f"/api/v1/products/{product.id}").json()["eligible_for_adoption"] is True

    api.put(
        f"{_url(category.id)}/{association['id']}",
        json={"is_required": True, "is_filterable": False, "display_order": 0, "version": 1},
    )

    stored = api.get(f"/api/v1/products/{product.id}").json()
    assert stored["eligible_for_adoption"] is False
    assert stored["status"] == "ACTIVE"
    assert stored["version"] == product.version


def test_applicable_attributes_without_inheritance(api, session_factory) -> None:
    unit = factories.unit(session_factory)
    lacteos = factories.category(session_factory, "LACTEOS")
    leches = factories.category(session_factory, "LECHES", parent=lacteos.id)
    organicos = factories.category(session_factory, "ORGANICOS")
    fat = factories.definition(session_factory, "PORCENTAJE_GRASA")
    cert = factories.definition(session_factory, "CERTIFICACION", "TEXT")
    brand = factories.definition(session_factory, "MARCA_LOCAL", "TEXT")
    factories.category_attribute(session_factory, lacteos.id, fat.id, required=True)
    factories.category_attribute(session_factory, organicos.id, cert.id, required=False, filterable=True)
    factories.category_attribute(session_factory, leches.id, cert.id, required=True)
    factories.category_attribute(session_factory, leches.id, brand.id, required=False, status="INACTIVE")
    product = factories.product(session_factory, unit.id)
    factories.product_category(session_factory, product.id, leches.id, is_primary=True)
    factories.product_category(session_factory, product.id, organicos.id, is_primary=False)

    items = api.get(f"/api/v1/products/{product.id}/applicable-attributes").json()

    assert [item["code"] for item in items] == ["CERTIFICACION"]
    assert items[0]["is_required"] is True
    assert items[0]["is_filterable"] is True
    assert set(items[0]["category_ids"]) == {str(leches.id), str(organicos.id)}


def test_deactivate_requires_categories_deactivate(api, api_as, session_factory) -> None:
    category = factories.category(session_factory, "LECHES")
    fat = factories.definition(session_factory, "GRASA")
    association = api.post(_url(category.id), json={"attribute_definition_id": str(fat.id)}).json()

    response = api_as("categories:update").post(
        f"{_url(category.id)}/{association['id']}/deactivate", json={"version": 1}
    )

    assert response.status_code == 403
