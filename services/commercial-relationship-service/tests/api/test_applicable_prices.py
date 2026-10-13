"""Historia 5 de la 010: precio aplicable (T062; FR-055; aclaración 2; SC-009) con la spec 019."""

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
    # Spec 019: productos sin precio; cada presentación vendible tiene su precio explícito en una lista.
    p1 = adopt(admin, company, fake_catalog, internal_code="P1")
    p2 = adopt(admin, company, fake_catalog, internal_code="P2")
    p3 = adopt(admin, company, fake_catalog, internal_code="P3")
    box = adopt_presentation(admin, company, fake_catalog, p1)
    unit1 = adopt_presentation(admin, company, fake_catalog, p1)
    unit2 = adopt_presentation(admin, company, fake_catalog, p2)
    unit3 = adopt_presentation(admin, company, fake_catalog, p3)
    default = create_price_list(admin, company, code="MINORISTA", is_default=True)
    explicit = create_price_list(admin, company, code="MAYORISTA")
    create_price(admin, company, default, p1, unit_price="170000", company_product_presentation_id=box["id"],
                 valid_from=_iso(NOW - timedelta(days=2)))
    create_price(admin, company, default, p2, unit_price="15000", company_product_presentation_id=unit2["id"],
                 valid_from=_iso(NOW - timedelta(days=2)))
    return {"p1": p1, "p2": p2, "p3": p3, "box": box, "unit1": unit1, "unit2": unit2, "unit3": unit3,
            "default": default, "explicit": explicit}


def _resolve(client, company, lines, **extra):
    return client.post(f"/api/v1/companies/{company}/applicable-prices/resolve", json={"lines": lines, **extra})


def _line(world, product, presentation, **extra):
    return {"company_product_id": world[product]["id"], "company_product_presentation_id": world[presentation]["id"], **extra}


def test_scenarios_1_to_4_in_one_request(admin, company, world):
    response = _resolve(admin, company, [
        _line(world, "p1", "box", line_id="a"),
        _line(world, "p2", "unit2", line_id="b"),
        _line(world, "p3", "unit3", line_id="c"),
        _line(world, "p1", "unit1", line_id="d"),
    ])

    assert response.status_code == 200, response.text
    a, b, c, d = response.json()["items"]
    assert (a["resolution"], a["basis"], a["unit_price"], a["currency_code"]) == ("PRICE_LIST_ITEM", "PRESENTATION", "170000.00", "COP")
    assert a["price_list_id"] == world["default"]["id"] and a["price_list_item_id"] is not None
    assert (b["resolution"], b["basis"], b["unit_price"]) == ("PRICE_LIST_ITEM", "PRESENTATION", "15000.00")
    # Spec 019: sin precio de la presentación no hay precio (ni respaldo en el producto ni conversión desde la caja).
    for item in (c, d):
        assert (item["resolution"], item["basis"], item["unit_price"], item["price_list_item_id"]) == (
            "NO_PRICE_IN_LIST", None, None, None)
    assert [a["line_id"], b["line_id"], c["line_id"], d["line_id"]] == ["a", "b", "c", "d"]


def test_line_without_presentation_is_rejected_spec_019(admin, company, world):
    response = _resolve(admin, company, [{"company_product_id": world["p2"]["id"]}])
    assert response.status_code == 422 and code_of(response) == "VALIDATION_ERROR"
    assert "company_product_presentation_id" in response.text


def test_without_applicable_default_list_spec_019(admin, company, world):
    assert admin.post(f"/api/v1/price-lists/{world['default']['id']}/deactivate", json={"version": 1}).status_code == 200
    [line] = _resolve(admin, company, [_line(world, "p2", "unit2")]).json()["items"]
    assert (line["resolution"], line["unit_price"]) == ("NO_APPLICABLE_PRICE_LIST", None)


def test_scenario_3a_explicit_list_without_price_has_no_fallback(admin, company, world):
    [line] = _resolve(admin, company, [_line(world, "p3", "unit3", price_list_id=world["explicit"]["id"])]).json()["items"]
    assert line["resolution"] == "NO_PRICE_IN_LIST" and line["unit_price"] is None


def test_scenario_5_explicit_list_not_applicable(admin, company, other_company, world):
    admin.post(f"/api/v1/price-lists/{world['explicit']['id']}/deactivate", json={"version": 1})
    lines = [
        _line(world, "p2", "unit2", price_list_id=world["explicit"]["id"]),
        _line(world, "p2", "unit2", price_list_id=str(uuid4())),
    ]
    items = _resolve(admin, company, lines).json()["items"]
    assert [item["resolution"] for item in items] == ["PRICE_LIST_NOT_APPLICABLE"] * 2


def test_scenario_6_and_sc_009_history(admin, company, world):
    current = admin.get(f"/api/v1/companies/{company}/price-list-items",
                        params={"company_product_id": world["p2"]["id"]}).json()["items"][0]
    yesterday = _iso(NOW - timedelta(days=1))
    before = _resolve(admin, company, [_line(world, "p2", "unit2")], at=yesterday).json()["items"][0]

    changed = admin.post(f"/api/v1/price-list-items/{current['id']}/change-price",
                         json={"unit_price": "16000", "version": current["version"]})
    assert changed.status_code == 201, changed.text

    after = _resolve(admin, company, [_line(world, "p2", "unit2")], at=yesterday).json()["items"][0]
    assert before["unit_price"] == after["unit_price"] == "15000.00"
    latest = _resolve(admin, company, [_line(world, "p2", "unit2")], at=_iso(NOW + timedelta(minutes=5))).json()["items"][0]
    assert latest["unit_price"] == "16000.00"


def test_scenario_7_batch_limits(admin, company, world):
    line = _line(world, "p1", "box")
    response = _resolve(admin, company, [line] * 101)
    assert response.status_code == 422 and code_of(response) == "BATCH_LIMIT_EXCEEDED"
    assert _resolve(admin, company, []).status_code == 422


def test_isolation_and_permissions(as_user, admin, company, other_company, world):
    line = [_line(world, "p1", "box")]
    assert _resolve(admin, other_company, line).status_code == 404
    assert _resolve(as_user("ventas.test"), company, line).status_code == 200
    assert _resolve(as_user("inventario.test"), company, line).status_code == 403
