"""Historia 3: productos globales (FR-025 a FR-033, FR-029, FR-006, RC-10, RC-13, RC-16)."""

from uuid import UUID, uuid4

from tests import factories

URL = "/api/v1/products"


def _body(unit_id, **overrides) -> dict:
    return {
        "product_type": "GOOD",
        "canonical_name": "Arroz blanco 500 g",
        "base_unit_id": str(unit_id),
        **overrides,
    }


def _update_body(product: dict, **changes) -> dict:
    return {
        "canonical_name": product["canonical_name"],
        "description": product["description"],
        "global_brand_id": product["global_brand_id"],
        "manufacturer_organization_id": product["manufacturer_organization_id"],
        "base_unit_id": product["base_unit_id"],
        "version": product["version"],
        **changes,
    }


def test_create_product_with_brand(api, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    brand = factories.brand(session_factory, "ACME")

    response = api.post(URL, json=_body(unit.id, global_brand_id=str(brand.id)))

    assert response.status_code == 201
    product = response.json()
    assert product["status"] == "ACTIVE"
    assert product["global_brand_id"] == str(brand.id)
    assert product["warnings"] == []
    assert product["first_used_at"] is None


def test_inactive_brand_rejected(api, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    brand = factories.brand(session_factory, "OLD", status="INACTIVE")

    response = api.post(URL, json=_body(unit.id, global_brand_id=str(brand.id)))

    assert response.status_code == 422
    assert response.json()["code"] == "PRODUCT_CATALOG.REFERENCE_INACTIVE"


def test_manufacturer_not_found_unavailable_and_denied(api, session_factory, fake_manufacturer_directory) -> None:
    unit = factories.unit(session_factory, "UND")
    body = _body(unit.id, manufacturer_organization_id=str(uuid4()))

    not_found = api.post(URL, json=body)
    assert not_found.status_code == 422
    assert not_found.json()["code"] == "PRODUCT_CATALOG.MANUFACTURER_NOT_FOUND"

    fake_manufacturer_directory.mode = "unavailable"
    unavailable = api.post(URL, json=body)
    assert unavailable.status_code == 503
    assert unavailable.json()["code"] == "PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE"

    fake_manufacturer_directory.mode = "denied"
    denied = api.post(URL, json=body)
    assert denied.status_code == 403
    assert denied.json()["code"] == "PRODUCT_CATALOG.MANUFACTURER_ACCESS_DENIED"

    assert api.get(URL).json()["total_records"] == 0


def test_update_without_manufacturer_change_ignores_party_identity(
    api, session_factory, fake_manufacturer_directory
) -> None:
    unit = factories.unit(session_factory, "UND")
    manufacturer = uuid4()
    fake_manufacturer_directory.existing.add(manufacturer)
    product = api.post(URL, json=_body(unit.id, manufacturer_organization_id=str(manufacturer))).json()

    fake_manufacturer_directory.mode = "unavailable"
    response = api.put(f"{URL}/{product['id']}", json=_update_body(product, description="Nueva"))

    assert response.status_code == 200
    assert response.json()["description"] == "Nueva"


def test_assigning_unknown_manufacturer_keeps_previous(api, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    product = api.post(URL, json=_body(unit.id)).json()

    response = api.put(
        f"{URL}/{product['id']}",
        json=_update_body(product, manufacturer_organization_id=str(uuid4())),
    )

    assert response.json()["code"] == "PRODUCT_CATALOG.MANUFACTURER_NOT_FOUND"
    assert api.get(f"{URL}/{product['id']}").json()["manufacturer_organization_id"] is None


def test_incomplete_product_is_editable_but_not_eligible(api, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    product = api.post(URL, json=_body(unit.id)).json()

    assert product["completeness"]["is_complete"] is False
    assert "NO_ACTIVE_CATEGORY" in product["completeness"]["issues"]
    assert "NO_ACTIVE_PRESENTATION" in product["completeness"]["issues"]
    assert product["eligible_for_adoption"] is False

    edited = api.put(f"{URL}/{product['id']}", json=_update_body(product, canonical_name="Arroz blanco"))
    assert edited.status_code == 200


def test_required_attributes_of_all_categories(api, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    leches = factories.category(session_factory, "LECHES")
    organicos = factories.category(session_factory, "ORGANICOS")
    fat = factories.definition(session_factory, "PORCENTAJE_GRASA", "DECIMAL")
    cert = factories.definition(session_factory, "CERTIFICACION", "TEXT")
    factories.category_attribute(session_factory, leches.id, fat.id)
    factories.category_attribute(session_factory, organicos.id, cert.id)
    product = factories.product(session_factory, unit.id, "Leche orgánica")
    factories.product_category(session_factory, product.id, leches.id, is_primary=True)
    factories.product_category(session_factory, product.id, organicos.id, is_primary=False)
    factories.presentation(session_factory, product.id)
    factories.value(session_factory, product.id, fat.id, decimal_value=3.5)

    completeness = api.get(f"{URL}/{product.id}/completeness").json()

    assert completeness["is_complete"] is False
    assert completeness["issues"] == ["MISSING_REQUIRED_ATTRIBUTE"]
    assert completeness["missing_attribute_definition_ids"] == [str(cert.id)]


def test_complete_product_is_eligible_and_inactivation_removes_eligibility(api, session_factory) -> None:
    product, _, _ = factories.complete_product(session_factory)

    current = api.get(f"{URL}/{product.id}").json()
    assert current["eligible_for_adoption"] is True

    deactivated = api.post(f"{URL}/{product.id}/deactivate", json={"version": current["version"]}).json()
    assert deactivated["status"] == "INACTIVE"
    assert deactivated["completeness"]["is_complete"] is True
    assert deactivated["eligible_for_adoption"] is False


def test_inactive_category_keeps_product_complete(api, session_factory) -> None:
    product, category, _ = factories.complete_product(session_factory)
    api.post(f"/api/v1/categories/{category.id}/deactivate", json={"version": 1})

    assert api.get(f"{URL}/{product.id}").json()["eligible_for_adoption"] is True


def test_inactive_base_unit_keeps_product_complete(api, session_factory) -> None:
    product, _, unit = factories.complete_product(session_factory)
    api.post(f"/api/v1/units-of-measure/{unit.id}/deactivate", json={"version": 1})

    assert api.get(f"{URL}/{product.id}").json()["completeness"]["is_complete"] is True


def test_base_unit_change_with_and_without_first_use(api, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    other = factories.unit(session_factory, "KG")
    free = api.post(URL, json=_body(unit.id)).json()

    changed = api.put(f"{URL}/{free['id']}", json=_update_body(free, base_unit_id=str(other.id)))
    assert changed.status_code == 200

    used = factories.product(session_factory, unit.id, "Usado", first_used=True)
    used_json = api.get(f"{URL}/{used.id}").json()
    locked = api.put(f"{URL}/{used.id}", json=_update_body(used_json, base_unit_id=str(other.id)))
    assert locked.status_code == 422
    assert locked.json()["code"] == "PRODUCT_CATALOG.BASE_UNIT_LOCKED_BY_FIRST_USE"


def test_immutable_fields(api, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    product = api.post(URL, json=_body(unit.id)).json()

    for field, value in (("product_type", "GOOD"), ("first_used_at", "2026-01-01T00:00:00Z")):
        response = api.put(f"{URL}/{product['id']}", json={**_update_body(product), field: value})
        assert response.json()["code"] == "PRODUCT_CATALOG.IMMUTABLE_FIELD"


def test_duplicate_warning_does_not_block(api, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    brand = factories.brand(session_factory, "ACME")
    other_brand = factories.brand(session_factory, "OTRA")
    first = api.post(URL, json=_body(unit.id, canonical_name="Café  Molido", global_brand_id=str(brand.id))).json()

    same = api.post(URL, json=_body(unit.id, canonical_name="cafe molido", global_brand_id=str(brand.id)))
    different_brand = api.post(
        URL, json=_body(unit.id, canonical_name="Cafe molido", global_brand_id=str(other_brand.id))
    )
    no_brand_a = api.post(URL, json=_body(unit.id, canonical_name="Sal"))
    no_brand_b = api.post(URL, json=_body(unit.id, canonical_name="SAL"))

    assert same.status_code == 201
    assert same.json()["warnings"][0]["code"] == "POSSIBLE_DUPLICATE"
    assert same.json()["warnings"][0]["matching_product_ids"] == [first["id"]]
    assert different_brand.json()["warnings"] == []
    assert no_brand_a.json()["warnings"] == []
    assert no_brand_b.json()["warnings"][0]["matching_product_ids"] == [no_brand_a.json()["id"]]


def test_stale_version_and_permissions(api, api_as, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    product = api.post(URL, json=_body(unit.id)).json()
    assert api.put(f"{URL}/{product['id']}", json=_update_body(product, description="a")).status_code == 200

    stale = api.put(f"{URL}/{product['id']}", json=_update_body(product, description="b"))
    assert stale.json()["code"] == "PRODUCT_CATALOG.VERSION_CONFLICT"

    assert api_as("products:read").post(URL, json=_body(unit.id)).status_code == 403
    reader = api_as("products:update")
    assert reader.post(f"{URL}/{product['id']}/deactivate", json={"version": 2}).status_code == 403


def test_reactivate_with_inactive_brand_allowed(api, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    brand = factories.brand(session_factory, "ACME")
    product = api.post(URL, json=_body(unit.id, global_brand_id=str(brand.id))).json()
    api.post(f"{URL}/{product['id']}/deactivate", json={"version": 1})
    api.post(f"/api/v1/brands/{brand.id}/deactivate", json={"version": 1})

    response = api.post(f"{URL}/{product['id']}/reactivate", json={"version": 2})

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"


def test_list_search_ignores_accents(api, session_factory) -> None:
    unit = factories.unit(session_factory, "UND")
    api.post(URL, json=_body(unit.id, canonical_name="Café molido"))
    api.post(URL, json=_body(unit.id, canonical_name="Arroz"))

    names = [item["canonical_name"] for item in api.get(f"{URL}?search=CAFE").json()["items"]]

    assert names == ["Café molido"]
    assert UUID(api.get(URL).json()["items"][0]["id"])
