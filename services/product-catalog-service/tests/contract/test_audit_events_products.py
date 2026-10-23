"""Eventos de productos y dependientes (feature 016; acciones PC 33–43 y 46–61; T058)."""

from __future__ import annotations

from tests import factories
from tests.contract.test_audit_events_simple_catalogs import check

V = "/api/v1"


def _items(payload):
    return payload["items"] if isinstance(payload, dict) else payload


def _product(session_factory):
    unit = factories.unit(session_factory)
    return factories.product(session_factory, unit.id)


def test_product_lifecycle(api, session_factory, outbox, clear_outbox) -> None:
    unit = factories.unit(session_factory, "UND")
    clear_outbox()
    created = api.post(f"{V}/products", json={"product_type": "GOOD", "canonical_name": "Arroz blanco 500 g",
                                              "base_unit_id": str(unit.id)})
    assert created.status_code == 201, created.text
    product = created.json()
    url = f"{V}/products/{product['id']}"
    body = {key: product[key] for key in ("canonical_name", "description", "global_brand_id",
                                          "manufacturer_organization_id", "base_unit_id", "version")}
    updated = api.put(url, json={**body, "description": "Grano largo"})
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert api.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    events = outbox()
    assert [e["action"] for e in events] == ["CREATE_PRODUCT", "UPDATE_PRODUCT", "DEACTIVATE_PRODUCT", "REACTIVATE_PRODUCT"]
    for event in events:
        check(event, event["action"], "Product", product["id"])
    assert events[0]["new_values"]["canonical_name"] == "Arroz blanco 500 g"
    assert events[1]["new_values"] == {"description": "Grano largo"}


def test_product_categories(api, session_factory, outbox, clear_outbox) -> None:
    product = _product(session_factory)
    arroz, granos = factories.category(session_factory, "ARROZ"), factories.category(session_factory, "GRANOS")
    clear_outbox()
    base = f"{V}/products/{product.id}/categories"
    first = api.post(base, json={"global_category_id": str(arroz.id)})
    assert first.status_code == 201, first.text
    second = api.post(base, json={"global_category_id": str(granos.id)})
    assert second.status_code == 201, second.text
    primary = api.post(f"{base}/{second.json()['id']}/set-primary", json={"version": second.json()["version"]})
    assert primary.status_code == 200, primary.text
    current = next(item for item in _items(api.get(base).json()) if item["id"] == first.json()["id"])
    removed = api.post(f"{base}/{first.json()['id']}/deactivate", json={"version": current["version"]})
    assert removed.status_code == 200, removed.text

    add_first, add_second, set_primary, deactivate = outbox()
    check(add_first, "ADD_PRODUCT_CATEGORY", "ProductCategory", first.json()["id"])
    check(add_second, "ADD_PRODUCT_CATEGORY", "ProductCategory", second.json()["id"])
    check(set_primary, "SET_PRIMARY_PRODUCT_CATEGORY", "ProductCategory", second.json()["id"])
    assert set_primary["previous_values"]["previous_primary_id"] == first.json()["id"]
    check(deactivate, "DEACTIVATE_PRODUCT_CATEGORY", "ProductCategory", first.json()["id"])


def test_presentation_lifecycle(api, session_factory, outbox, clear_outbox) -> None:
    product = _product(session_factory)
    clear_outbox()
    created = api.post(f"{V}/products/{product.id}/presentations", json={"code": "CAJA_X_20", "name": "Caja x 20", "base_quantity": 20})
    assert created.status_code == 201, created.text
    item = created.json()
    url = f"{V}/presentations/{item['id']}"
    body = {key: item[key] for key in ("name", "display_order", "packaging_type_id", "base_quantity", "content_quantity",
                                       "content_unit_id", "is_base", "version")}
    updated = api.put(url, json={**body, "name": "Caja de 20 unidades"})
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert api.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_PRODUCT_PRESENTATION", "UPDATE_PRODUCT_PRESENTATION", "DEACTIVATE_PRODUCT_PRESENTATION", "REACTIVATE_PRODUCT_PRESENTATION",
    ]
    for event in events:
        check(event, event["action"], "ProductPresentation", item["id"])
    assert events[1]["new_values"] == {"name": "Caja de 20 unidades"}


def test_identifiers(api, session_factory, outbox, clear_outbox) -> None:
    product = _product(session_factory)
    clear_outbox()
    base = f"{V}/products/{product.id}/identifiers"
    first = api.post(base, json={"identifier_type": "UPC", "value": "036000291452", "is_primary": True})
    assert first.status_code == 201, first.text
    second = api.post(base, json={"identifier_type": "UPC", "value": "012345678905"})
    assert second.status_code == 201, second.text
    primary = api.post(f"{base}/{second.json()['id']}/set-primary", json={"version": second.json()["version"]})
    assert primary.status_code == 200, primary.text
    current = next(item for item in _items(api.get(base).json()) if item["id"] == first.json()["id"])
    assert api.post(f"{base}/{first.json()['id']}/deactivate", json={"version": current["version"]}).status_code == 200
    assert api.post(f"{base}/{first.json()['id']}/reactivate", json={"version": current["version"] + 1}).status_code == 200

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_PRODUCT_IDENTIFIER", "CREATE_PRODUCT_IDENTIFIER", "SET_PRIMARY_PRODUCT_IDENTIFIER",
        "DEACTIVATE_PRODUCT_IDENTIFIER", "REACTIVATE_PRODUCT_IDENTIFIER",
    ]
    assert events[2]["entity_id"] == second.json()["id"]
    assert events[2]["previous_values"]["previous_primary_id"] == first.json()["id"]
    for event in events:
        check(event, event["action"], "ProductIdentifier", event["entity_id"])


def test_groups_and_assignments(api, session_factory, outbox, clear_outbox) -> None:
    product = _product(session_factory)
    group_type = api.post(f"{V}/group-types", json={"code": "LINEA", "name": "Línea", "allows_multiple": False}).json()
    clear_outbox()
    created = api.post(f"{V}/group-types/{group_type['id']}/groups", json={"code": "PREMIUM", "name": "Premium"})
    assert created.status_code == 201, created.text
    group = created.json()
    url = f"{V}/groups/{group['id']}"
    updated = api.put(url, json={"name": "Premium plus", "parent_group_id": None, "version": group["version"]})
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert api.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    assignments = f"{V}/products/{product.id}/group-assignments"
    assigned = api.post(assignments, json={"global_product_group_id": group["id"]})
    assert assigned.status_code == 201, assigned.text
    assignment = assigned.json()
    assert api.post(f"{assignments}/{assignment['id']}/deactivate", json={"version": assignment["version"]}).status_code == 200
    assert api.post(f"{assignments}/{assignment['id']}/reactivate", json={"version": assignment["version"] + 1}).status_code == 200

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_PRODUCT_GROUP", "UPDATE_PRODUCT_GROUP", "DEACTIVATE_PRODUCT_GROUP", "REACTIVATE_PRODUCT_GROUP",
        "CREATE_PRODUCT_GROUP_ASSIGNMENT", "DEACTIVATE_PRODUCT_GROUP_ASSIGNMENT", "REACTIVATE_PRODUCT_GROUP_ASSIGNMENT",
    ]
    for event in events[:4]:
        check(event, event["action"], "ProductGroup", group["id"])
    for event in events[4:]:
        check(event, event["action"], "ProductGroupAssignment", assignment["id"])


def test_assets(api, session_factory, outbox, clear_outbox) -> None:
    product = _product(session_factory)
    # Spec 024: las imágenes se auditan por presentación (`test_presentation_images_api.py`); aquí, una ficha técnica.
    image = {"asset_type": "TECHNICAL_SHEET", "file_name": "frente.png",
             "storage_uri": "s3://sio-assets/productos/frente.png", "mime_type": "image/png"}
    clear_outbox()
    base = f"{V}/products/{product.id}/assets"
    first = api.post(base, json={**image, "is_primary": True})
    assert first.status_code == 201, first.text
    second = api.post(base, json={**image, "file_name": "lado.png"})
    assert second.status_code == 201, second.text
    edited = api.put(f"{base}/{second.json()['id']}", json={"file_name": "lado-v2.png", "storage_uri": image["storage_uri"],
                                                            "mime_type": "image/png", "version": second.json()["version"]})
    assert edited.status_code == 200, edited.text
    primary = api.post(f"{base}/{second.json()['id']}/set-primary", json={"version": edited.json()["version"]})
    assert primary.status_code == 200, primary.text
    current = next(item for item in _items(api.get(base).json()) if item["id"] == first.json()["id"])
    assert api.post(f"{base}/{first.json()['id']}/deactivate", json={"version": current["version"]}).status_code == 200
    assert api.post(f"{base}/{first.json()['id']}/reactivate", json={"version": current["version"] + 1}).status_code == 200

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_PRODUCT_ASSET", "CREATE_PRODUCT_ASSET", "UPDATE_PRODUCT_ASSET", "SET_PRIMARY_PRODUCT_ASSET",
        "DEACTIVATE_PRODUCT_ASSET", "REACTIVATE_PRODUCT_ASSET",
    ]
    assert events[2]["new_values"] == {"file_name": "lado-v2.png"}
    assert events[3]["previous_values"]["previous_primary_id"] == first.json()["id"]
    for event in events:
        check(event, event["action"], "ProductAsset", event["entity_id"])
