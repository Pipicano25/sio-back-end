"""Eventos de atributos (feature 016; acciones PC 17–28 y 44–45; T057)."""

from __future__ import annotations

from tests import factories
from tests.contract.test_audit_events_simple_catalogs import check

V = "/api/v1"


def test_attribute_definition_and_options(api, outbox, clear_outbox) -> None:
    clear_outbox()
    color = api.post(f"{V}/attribute-definitions", json={"code": "COLOR", "name": "Color", "description": "Color",
                                                         "data_type": "OPTION"})
    assert color.status_code == 201, color.text
    definition = color.json()
    url = f"{V}/attribute-definitions/{definition['id']}"
    updated = api.put(url, json={"name": "Color principal", "description": "Color", "version": definition["version"]})
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert api.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    option = api.post(f"{url}/options", json={"code": "RED", "name": "Rojo", "display_order": 1})
    assert option.status_code == 201, option.text
    option_url = f"{url}/options/{option.json()['id']}"
    edited = api.put(option_url, json={"name": "Rojo vivo", "display_order": 3, "version": option.json()["version"]})
    assert edited.status_code == 200, edited.text
    version = edited.json()["version"]
    assert api.post(f"{option_url}/deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{option_url}/reactivate", json={"version": version + 1}).status_code == 200

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_ATTRIBUTE_DEFINITION", "UPDATE_ATTRIBUTE_DEFINITION", "DEACTIVATE_ATTRIBUTE_DEFINITION",
        "REACTIVATE_ATTRIBUTE_DEFINITION", "CREATE_ATTRIBUTE_OPTION", "UPDATE_ATTRIBUTE_OPTION",
        "DEACTIVATE_ATTRIBUTE_OPTION", "REACTIVATE_ATTRIBUTE_OPTION",
    ]
    for event in events[:4]:
        check(event, event["action"], "AttributeDefinition", definition["id"])
    for event in events[4:]:
        check(event, event["action"], "AttributeOption", option.json()["id"])
    assert events[5]["new_values"] == {"name": "Rojo vivo", "display_order": 3}


def test_category_attribute_lifecycle(api, session_factory, outbox, clear_outbox) -> None:
    category = factories.category(session_factory, "LACTEOS")
    fat = factories.definition(session_factory, "GRASA", "DECIMAL")
    clear_outbox()
    base = f"{V}/categories/{category.id}/attributes"
    created = api.post(base, json={"attribute_definition_id": str(fat.id), "is_required": False})
    assert created.status_code == 201, created.text
    association = created.json()
    url = f"{base}/{association['id']}"
    updated = api.put(url, json={"is_required": True, "is_filterable": False, "display_order": 0,
                                 "version": association["version"]})
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert api.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    assert api.post(f"{url}/reactivate", json={"version": version + 1}).status_code == 200

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_CATEGORY_ATTRIBUTE", "UPDATE_CATEGORY_ATTRIBUTE", "DEACTIVATE_CATEGORY_ATTRIBUTE", "REACTIVATE_CATEGORY_ATTRIBUTE",
    ]
    for event in events:
        check(event, event["action"], "CategoryAttribute", association["id"])
    assert events[1]["previous_values"]["is_required"] is False and events[1]["new_values"]["is_required"] is True


def test_attribute_value_set_and_delete(api, session_factory, outbox, clear_outbox) -> None:
    unit = factories.unit(session_factory)
    leches = factories.category(session_factory, "LECHES")
    fat = factories.definition(session_factory, "GRASA", "DECIMAL")
    factories.category_attribute(session_factory, leches.id, fat.id)
    product = factories.product(session_factory, unit.id, "Leche")
    factories.product_category(session_factory, product.id, leches.id)
    clear_outbox()
    url = f"{V}/products/{product.id}/attribute-values/{fat.id}"
    created = api.put(url, json={"decimal_value": 3.5})
    assert created.status_code in (200, 201), created.text
    replaced = api.put(url, json={"decimal_value": 2, "version": created.json()["version"]})
    assert replaced.status_code == 200, replaced.text
    deleted = api.delete(f"{url}?version={replaced.json()['version']}")
    assert deleted.status_code in (200, 204), deleted.text

    first, second, delete = outbox()
    value_id = created.json()["id"]
    check(first, "SET_PRODUCT_ATTRIBUTE_VALUE", "ProductAttributeValue", value_id)
    assert first["previous_values"] is None
    check(second, "SET_PRODUCT_ATTRIBUTE_VALUE", "ProductAttributeValue", value_id)
    assert second["previous_values"]["decimal_value"] != second["new_values"]["decimal_value"]
    check(delete, "DELETE_PRODUCT_ATTRIBUTE_VALUE", "ProductAttributeValue", value_id)
    assert delete["new_values"] is None
    assert delete["previous_values"]["global_product_id"] == str(product.id)
