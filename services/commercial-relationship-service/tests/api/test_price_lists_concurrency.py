"""Concurrencia de listas y precios (T053; RC-05, RC-06, RC-12; SC-006)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.api.concurrency import race
from tests.api.helpers import adopt, create_price, create_price_list, price_list_update_body

TOMORROW = (datetime.now(UTC) + timedelta(days=1)).isoformat()


def test_two_simultaneous_default_lists_leave_one(app, user_token, as_user, company):
    admin = as_user("admin.test")
    rows = [create_price_list(admin, company, code=f"L{index}") for index in range(2)]

    results = race(
        app,
        user_token("admin.test"),
        [("PUT", f"/api/v1/price-lists/{row['id']}", price_list_update_body(row, is_default=True)) for row in rows],
    )

    assert all(response.status_code in {200, 409} for response in results), [r.text for r in results]
    listed = admin.get(f"/api/v1/companies/{company}/price-lists").json()["items"]
    assert sum(row["is_default"] for row in listed) == 1


def test_two_simultaneous_overlapping_prices(app, user_token, as_user, company, fake_catalog):
    admin = as_user("admin.test")
    product = adopt(admin, company, fake_catalog)
    price_list = create_price_list(admin, company)
    body = {"price_list_id": price_list["id"], "company_product_id": product["id"], "unit_price": "1"}

    results = race(app, user_token("admin.test"), [("POST", f"/api/v1/companies/{company}/price-list-items", body)] * 2)

    assert sorted(response.status_code for response in results) == [201, 409], [r.text for r in results]
    conflict = next(response for response in results if response.status_code == 409)
    assert conflict.json()["code"] == "COMMERCIAL_RELATIONSHIP.PRICE_PERIOD_OVERLAP"


def test_two_simultaneous_change_price_on_same_price(app, user_token, as_user, company, fake_catalog):
    admin = as_user("admin.test")
    product = adopt(admin, company, fake_catalog)
    price_list = create_price_list(admin, company)
    current = create_price(admin, company, price_list, product)
    url = f"/api/v1/price-list-items/{current['id']}/change-price"

    results = race(
        app,
        user_token("admin.test"),
        [("POST", url, {"unit_price": price, "effective_from": TOMORROW, "version": 1}) for price in ("16000", "17000")],
    )

    assert sorted(response.status_code for response in results) == [201, 409], [r.text for r in results]
    active = admin.get(f"/api/v1/companies/{company}/price-list-items").json()["items"]
    assert len(active) == 2  # el cerrado y uno nuevo, sin solapamientos
