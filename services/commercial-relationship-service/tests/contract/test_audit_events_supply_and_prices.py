"""Eventos de abastecimiento y precios (feature 016; acciones CR 19–35; T037)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tests.api.helpers import (
    adopt,
    condition_update_body,
    create_condition,
    create_price,
    create_price_list,
    create_supplier_product,
    price_list_update_body,
    price_update_body,
    supplier,
    supplier_product_update_body,
)
from tests.contract.test_audit_events_products import check


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


def _lifecycle(admin, url: str, update_body: dict) -> None:
    updated = admin.put(url, json=update_body)
    assert updated.status_code == 200, updated.text
    version = updated.json()["version"]
    assert admin.post(f"{url}/deactivate", json={"version": version}).status_code == 200
    reactivated = admin.post(f"{url}/reactivate", json={"version": version + 1})
    assert reactivated.status_code == 200, reactivated.text


def test_supplier_product_lifecycle(admin, company, fake_catalog, fake_party, outbox, clear_outbox) -> None:
    product = adopt(admin, company, fake_catalog)
    provider = supplier(admin, company, fake_party)
    clear_outbox()
    relation = create_supplier_product(admin, company, provider, product, fake_catalog)
    _lifecycle(admin, f"/api/v1/supplier-products/{relation['id']}",
               supplier_product_update_body(relation, priority=7))

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_SUPPLIER_PRODUCT", "UPDATE_SUPPLIER_PRODUCT", "DEACTIVATE_SUPPLIER_PRODUCT", "REACTIVATE_SUPPLIER_PRODUCT",
    ]
    for event in events:
        check(event, event["action"], "SupplierProduct", relation["id"], company)
    assert events[1]["new_values"] == {"priority": 7}


def test_supplier_payment_condition_lifecycle(admin, company, fake_party, fake_payment, outbox, clear_outbox) -> None:
    provider = supplier(admin, company, fake_party)
    clear_outbox()
    condition = create_condition(admin, company, provider, fake_payment)
    _lifecycle(admin, f"/api/v1/supplier-payment-conditions/{condition['id']}",
               condition_update_body(condition, payment_terms_days=45))

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_SUPPLIER_PAYMENT_CONDITION", "UPDATE_SUPPLIER_PAYMENT_CONDITION",
        "DEACTIVATE_SUPPLIER_PAYMENT_CONDITION", "REACTIVATE_SUPPLIER_PAYMENT_CONDITION",
    ]
    for event in events:
        check(event, event["action"], "SupplierPaymentCondition", condition["id"], company)
    assert events[1]["previous_values"] == {"payment_terms_days": 30}
    assert events[1]["new_values"] == {"payment_terms_days": 45}


def test_price_list_lifecycle(admin, company, outbox, clear_outbox) -> None:
    clear_outbox()
    price_list = create_price_list(admin, company)
    _lifecycle(admin, f"/api/v1/price-lists/{price_list['id']}", price_list_update_body(price_list, name="Mayorista"))

    events = outbox()
    assert [e["action"] for e in events] == [
        "CREATE_PRICE_LIST", "UPDATE_PRICE_LIST", "DEACTIVATE_PRICE_LIST", "REACTIVATE_PRICE_LIST",
    ]
    for event in events:
        check(event, event["action"], "PriceList", price_list["id"], company)
    assert events[1]["new_values"] == {"name": "Mayorista"}


def test_price_list_item_lifecycle_and_change_price(admin, company, fake_catalog, outbox, clear_outbox) -> None:
    product = adopt(admin, company, fake_catalog)
    other_product = adopt(admin, company, fake_catalog, internal_code="000046")
    price_list = create_price_list(admin, company)
    clear_outbox()
    item = create_price(admin, company, price_list, product, valid_from=_iso(datetime.now(UTC) - timedelta(days=1)))
    url = f"/api/v1/price-list-items/{item['id']}"
    future = create_price(admin, company, price_list, other_product, unit_price="17000.00",
                          valid_from=_iso(datetime.now(UTC) + timedelta(days=30)))
    edited = admin.put(f"/api/v1/price-list-items/{future['id']}", json=price_update_body(future, unit_price="17500.00"))
    assert edited.status_code == 200, edited.text
    changed = admin.post(f"{url}/change-price", json={"unit_price": "16000", "version": item["version"]})
    assert changed.status_code == 201, changed.text
    new_item = changed.json()["item"]
    new_url = f"/api/v1/price-list-items/{new_item['id']}"
    assert admin.post(f"{new_url}/deactivate", json={"version": new_item["version"]}).status_code == 200
    assert admin.post(f"{new_url}/reactivate", json={"version": new_item["version"] + 1}).status_code == 200

    create, create_future, update, change, deactivate, reactivate = outbox()
    check(create, "CREATE_PRICE_LIST_ITEM", "PriceListItem", item["id"], company)
    check(update, "UPDATE_PRICE_LIST_ITEM", "PriceListItem", future["id"], company)
    assert update["previous_values"] == {"unit_price": "17000.0000"} and update["new_values"] == {"unit_price": "17500.0000"}
    check(change, "CHANGE_PRICE_LIST_ITEM_PRICE", "PriceListItem", new_item["id"], company)
    assert change["previous_values"]["previous_item_id"] == item["id"]
    assert change["previous_values"]["unit_price"] == "15000.0000"
    assert change["new_values"]["unit_price"] == "16000.0000"
    check(deactivate, "DEACTIVATE_PRICE_LIST_ITEM", "PriceListItem", new_item["id"], company)
    check(reactivate, "REACTIVATE_PRICE_LIST_ITEM", "PriceListItem", new_item["id"], company)
