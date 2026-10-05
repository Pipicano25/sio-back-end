"""Historia 5 de la 010: precio aplicable (T062; FR-055; aclaración 2; SC-009)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from tests.api.helpers import adopt, adopt_presentation, code_of, create_price, create_price_list

NOW = datetime.now(UTC)


def _iso(moment):
    return moment.isoformat().replace("+00:00", "Z")


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


@pytest.fixture
def world(admin, company, fake_catalog):
    p1 = adopt(admin, company, fake_catalog, internal_code="P1", sale_price="1000.00")
    p2 = adopt(admin, company, fake_catalog, internal_code="P2", sale_price="2000.00")
    p3 = adopt(admin, company, fake_catalog, internal_code="P3", sale_price="3000.00")
    box = adopt_presentation(admin, company, fake_catalog, p1)
    default = create_price_list(admin, company, code="MINORISTA", is_default=True)
    explicit = create_price_list(admin, company, code="MAYORISTA")
    create_price(admin, company, default, p1, unit_price="170000", company_product_presentation_id=box["id"],
                 valid_from=_iso(NOW - timedelta(days=2)))
    create_price(admin, company, default, p2, unit_price="15000", valid_from=_iso(NOW - timedelta(days=2)))
    return {"p1": p1, "p2": p2, "p3": p3, "box": box, "default": default, "explicit": explicit}


def _resolve(client, company, lines, **extra):
    return client.post(f"/api/v1/companies/{company}/applicable-prices/resolve", json={"lines": lines, **extra})


def test_scenarios_1_to_4_in_one_request(admin, company, world):
    response = _resolve(admin, company, [
        {"line_id": "a", "company_product_id": world["p1"]["id"], "company_product_presentation_id": world["box"]["id"]},
        {"line_id": "b", "company_product_id": world["p2"]["id"], "company_product_presentation_id": None},
        {"line_id": "c", "company_product_id": world["p3"]["id"]},
    ])

    assert response.status_code == 200, response.text
    a, b, c = response.json()["items"]
    assert (a["resolution"], a["basis"], a["unit_price"], a["currency_code"]) == ("PRICE_LIST_ITEM", "PRESENTATION", "170000.00", "COP")
    assert a["price_list_id"] == world["default"]["id"] and a["price_list_item_id"] is not None
    assert (b["resolution"], b["basis"], b["unit_price"]) == ("PRICE_LIST_ITEM", "BASE_UNIT", "15000.00")
    assert (c["resolution"], c["basis"], c["unit_price"], c["price_list_id"]) == ("COMPANY_PRODUCT_SALE_PRICE", "BASE_UNIT", "3000.00", None)
    assert [a["line_id"], b["line_id"], c["line_id"]] == ["a", "b", "c"]


def test_scenario_3a_explicit_list_without_price_has_no_fallback(admin, company, world):
    [line] = _resolve(admin, company, [{"company_product_id": world["p3"]["id"], "price_list_id": world["explicit"]["id"]}]).json()["items"]
    assert line["resolution"] == "NO_PRICE_IN_LIST" and line["unit_price"] is None


def test_scenario_5_explicit_list_not_applicable(admin, company, other_company, world):
    admin.post(f"/api/v1/price-lists/{world['explicit']['id']}/deactivate", json={"version": 1})
    lines = [
        {"company_product_id": world["p2"]["id"], "price_list_id": world["explicit"]["id"]},
        {"company_product_id": world["p2"]["id"], "price_list_id": str(uuid4())},
    ]
    items = _resolve(admin, company, lines).json()["items"]
    assert [item["resolution"] for item in items] == ["PRICE_LIST_NOT_APPLICABLE"] * 2


def test_scenario_6_and_sc_009_history(admin, company, world):
    current = admin.get(f"/api/v1/companies/{company}/price-list-items",
                        params={"company_product_id": world["p2"]["id"]}).json()["items"][0]
    yesterday = _iso(NOW - timedelta(days=1))
    before = _resolve(admin, company, [{"company_product_id": world["p2"]["id"]}], at=yesterday).json()["items"][0]

    changed = admin.post(f"/api/v1/price-list-items/{current['id']}/change-price",
                         json={"unit_price": "16000", "version": current["version"]})
    assert changed.status_code == 201, changed.text

    after = _resolve(admin, company, [{"company_product_id": world["p2"]["id"]}], at=yesterday).json()["items"][0]
    assert before["unit_price"] == after["unit_price"] == "15000.00"
    latest = _resolve(admin, company, [{"company_product_id": world["p2"]["id"]}], at=_iso(NOW + timedelta(minutes=5))).json()["items"][0]
    assert latest["unit_price"] == "16000.00"


def test_scenario_7_batch_limits(admin, company, world):
    line = {"company_product_id": world["p1"]["id"]}
    response = _resolve(admin, company, [line] * 101)
    assert response.status_code == 422 and code_of(response) == "BATCH_LIMIT_EXCEEDED"
    assert _resolve(admin, company, []).status_code == 422


def test_isolation_and_permissions(as_user, admin, company, other_company, world):
    line = [{"company_product_id": world["p1"]["id"]}]
    assert _resolve(admin, other_company, line).status_code == 404
    assert _resolve(as_user("ventas.test"), company, line).status_code == 200
    assert _resolve(as_user("inventario.test"), company, line).status_code == 403
