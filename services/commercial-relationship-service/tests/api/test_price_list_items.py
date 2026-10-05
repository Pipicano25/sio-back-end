"""Historia 4 de la 010, precios de lista (T052; FR-050 a FR-054a, FR-057; aclaraciones 1 y 5; I2; H-04)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tests.api.helpers import (
    adopt,
    adopt_presentation,
    code_of,
    create_price,
    create_price_list,
    price_update_body,
)

URL = "/api/v1/companies/{company}/price-list-items"


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


NOW = datetime.now(UTC)
TOMORROW = _iso(NOW + timedelta(days=1))
NEXT_WEEK = _iso(NOW + timedelta(days=7))
YESTERDAY = _iso(NOW - timedelta(days=1))


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


@pytest.fixture
def world(admin, company, fake_catalog):
    product = adopt(admin, company, fake_catalog)
    return {"product": product, "list": create_price_list(admin, company, is_default=True)}


def _post(client, company, body):
    return client.post(URL.format(company=company), json=body)


def test_scenario_4_creates_price_with_list_currency(admin, company, world):
    created = create_price(admin, company, world["list"], world["product"])
    assert created["status"] == "ACTIVE" and created["unit_price"] == "15000.00" and created["currency_code"] == "COP"
    assert created["valid_to"] is None


def test_scenarios_5_and_6_overlap_and_contiguous(admin, company, world):
    current = create_price(admin, company, world["list"], world["product"], valid_from=YESTERDAY)

    overlap = _post(admin, company, {"price_list_id": world["list"]["id"], "company_product_id": world["product"]["id"],
                                     "unit_price": "16000", "valid_from": TOMORROW})
    assert overlap.status_code == 409 and code_of(overlap) == "PRICE_PERIOD_OVERLAP"

    closed = admin.put(f"/api/v1/price-list-items/{current['id']}", json=price_update_body(current, valid_to=TOMORROW))
    assert closed.status_code == 200, closed.text
    create_price(admin, company, world["list"], world["product"], unit_price="16000", valid_from=TOMORROW)


def test_scenario_7_in_effect_price_not_modifiable(admin, company, world):
    current = create_price(admin, company, world["list"], world["product"], valid_from=YESTERDAY)
    url = f"/api/v1/price-list-items/{current['id']}"

    for overrides in ({"unit_price": "17000"}, {"valid_from": _iso(NOW - timedelta(days=3))}):
        response = admin.put(url, json=price_update_body(current, **overrides))
        assert response.status_code == 422 and code_of(response) == "PRICE_IN_EFFECT_NOT_MODIFIABLE"

    past = admin.put(url, json=price_update_body(current, valid_to=_iso(NOW - timedelta(hours=1))))
    assert past.status_code == 422 and code_of(past) == "VALIDITY_INVALID"


def test_i2_postponing_valid_to_allowed_unless_overlap(admin, company, world):
    current = create_price(admin, company, world["list"], world["product"], valid_from=YESTERDAY, valid_to=TOMORROW)
    later = create_price(admin, company, world["list"], world["product"], unit_price="16000", valid_from=NEXT_WEEK)
    url = f"/api/v1/price-list-items/{current['id']}"

    postponed = admin.put(url, json=price_update_body(current, valid_to=_iso(NOW + timedelta(days=5))))
    assert postponed.status_code == 200 and postponed.json()["version"] == 2

    clash = admin.put(url, json=price_update_body(postponed.json(), valid_to=_iso(NOW + timedelta(days=10))))
    assert clash.status_code == 409 and code_of(clash) == "PRICE_PERIOD_OVERLAP"
    assert admin.get(url).json()["version"] == 2
    assert later["status"] == "ACTIVE"


def test_scenario_8_future_price_editable(admin, company, world):
    future = create_price(admin, company, world["list"], world["product"], valid_from=NEXT_WEEK)
    response = admin.put(f"/api/v1/price-list-items/{future['id']}", json=price_update_body(future, unit_price="15500.50"))
    assert response.status_code == 200 and response.json()["unit_price"] == "15500.50"


def test_scenario_8a_change_price(admin, company, world):
    current = create_price(admin, company, world["list"], world["product"], valid_from=YESTERDAY)
    url = f"/api/v1/price-list-items/{current['id']}/change-price"

    stale = admin.post(url, json={"unit_price": "16000", "effective_from": TOMORROW, "version": 9})
    assert stale.status_code == 409 and code_of(stale) == "VERSION_CONFLICT"

    response = admin.post(url, json={"unit_price": "16000", "effective_from": TOMORROW, "version": 1})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["previous"]["valid_to"] is not None and body["previous"]["version"] == 2
    assert body["item"]["unit_price"] == "16000.00" and body["item"]["valid_to"] is None
    assert body["item"]["valid_from"] == body["previous"]["valid_to"]
    assert response.headers["Location"] == f"/api/v1/price-list-items/{body['item']['id']}"

    out_of_period = admin.post(url, json={"unit_price": "1", "effective_from": YESTERDAY, "version": 2})
    assert out_of_period.status_code == 422 and code_of(out_of_period) == "PRICE_CHANGE_OUT_OF_PERIOD"


def test_h04_change_price_on_inactive_is_409(admin, company, world):
    current = create_price(admin, company, world["list"], world["product"], valid_from=YESTERDAY)
    admin.post(f"/api/v1/price-list-items/{current['id']}/deactivate", json={"version": 1})
    response = admin.post(f"/api/v1/price-list-items/{current['id']}/change-price", json={"unit_price": "1", "version": 2})
    assert response.status_code == 409 and code_of(response) == "INVALID_STATUS_TRANSITION"


def test_scenarios_9_and_10_zero_negative_and_currency_scale(admin, company, world):
    assert create_price(admin, company, world["list"], world["product"], unit_price="0")["unit_price"] == "0.00"

    clp = create_price_list(admin, company, code="CLP", currency_code="CLP")
    response = _post(admin, company, {"price_list_id": clp["id"], "company_product_id": world["product"]["id"], "unit_price": "1500.5"})
    assert response.status_code == 422 and code_of(response) == "PRICE_SCALE_NOT_ALLOWED"

    response = _post(admin, company, {"price_list_id": clp["id"], "company_product_id": world["product"]["id"], "unit_price": "-1"})
    assert response.status_code == 422 and code_of(response) == "VALIDATION_ERROR"


def test_scenario_11_presentation_checks(admin, company, fake_catalog, world):
    other_product = adopt(admin, company, fake_catalog, internal_code="000046")
    of_other = adopt_presentation(admin, company, fake_catalog, other_product)
    not_sellable = adopt_presentation(admin, company, fake_catalog, world["product"], is_sellable=False)

    for presentation, code in ((of_other, "PRESENTATION_OF_OTHER_PRODUCT"), (not_sellable, "PRESENTATION_NOT_SELLABLE")):
        response = _post(admin, company, {"price_list_id": world["list"]["id"], "company_product_id": world["product"]["id"],
                                          "unit_price": "1", "company_product_presentation_id": presentation["id"]})
        assert response.status_code == 422 and code_of(response) == code


def test_inactive_list_and_reactivation_overlap(admin, company, world):
    first = create_price(admin, company, world["list"], world["product"], valid_from=YESTERDAY)
    admin.post(f"/api/v1/price-list-items/{first['id']}/deactivate", json={"version": 1})
    create_price(admin, company, world["list"], world["product"], valid_from=YESTERDAY)
    response = admin.post(f"/api/v1/price-list-items/{first['id']}/reactivate", json={"version": 2})
    assert response.status_code == 409 and code_of(response) == "PRICE_PERIOD_OVERLAP"

    admin.post(f"/api/v1/price-lists/{world['list']['id']}/deactivate", json={"version": 1})
    response = _post(admin, company, {"price_list_id": world["list"]["id"], "company_product_id": world["product"]["id"], "unit_price": "1"})
    assert response.status_code == 422 and code_of(response) == "PRICE_LIST_INACTIVE"


def test_immutable_fields_and_filters(admin, company, world):
    current = create_price(admin, company, world["list"], world["product"], valid_from=YESTERDAY, valid_to=TOMORROW)
    create_price(admin, company, world["list"], world["product"], valid_from=NEXT_WEEK)

    response = admin.put(f"/api/v1/price-list-items/{current['id']}",
                         json={**price_update_body(current), "price_list_id": world["list"]["id"]})
    assert response.status_code == 422 and code_of(response) == "IMMUTABLE_FIELD"

    url = URL.format(company=company)
    assert admin.get(url).json()["total_records"] == 2
    applicable = admin.get(url, params={"applicable_at": _iso(NOW)}).json()
    assert [row["id"] for row in applicable["items"]] == [current["id"]]
    assert admin.get(url, params={"price_list_id": world["list"]["id"]}).json()["total_records"] == 2


def test_permissions(as_user, admin, company, world):
    created = create_price(admin, company, world["list"], world["product"])
    url = f"/api/v1/price-list-items/{created['id']}"
    assert as_user("ventas.test").get(url).status_code == 200
    assert as_user("ventas.test").post(url + "/change-price", json={"unit_price": "1", "version": 1}).status_code == 403
    assert as_user("supervisor.test").post(url + "/deactivate", json={"version": 1}).status_code == 403
    assert as_user("inventario.test").get(URL.format(company=company)).status_code == 403
