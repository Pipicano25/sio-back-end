"""Historia 4 de la 010, listas de precios (T051; FR-040 a FR-046; DS-05, DS-09)."""

from __future__ import annotations

import pytest

from tests.api.helpers import code_of, create_price_list, price_list_update_body

URL = "/api/v1/companies/{company}/price-lists"


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


def test_scenario_1_creates_default_list(admin, company):
    created = create_price_list(admin, company, code="MINORISTA", is_default=True)
    assert created["status"] == "ACTIVE" and created["is_default"] is True and created["currency_code"] == "COP"


def test_scenario_2_code_unique_case_insensitive(admin, company):
    create_price_list(admin, company, code="minorista")
    response = admin.post(URL.format(company=company), json={"code": "MINORISTA", "name": "Otra", "currency_code": "COP"})
    assert response.status_code == 409 and code_of(response) == "DUPLICATE_PRICE_LIST_CODE"


def test_scenario_3_default_swaps_within_currency(admin, company):
    first = create_price_list(admin, company, code="MINORISTA", is_default=True)
    usd = create_price_list(admin, company, code="EXPORT", currency_code="USD", is_default=True)
    second = create_price_list(admin, company, code="MAYORISTA", is_default=True)

    previous = admin.get(f"/api/v1/price-lists/{first['id']}").json()
    assert previous["is_default"] is False and previous["version"] == 2
    assert admin.get(f"/api/v1/price-lists/{usd['id']}").json()["is_default"] is True
    assert second["is_default"] is True


def test_currency_immutable_and_validity(admin, company):
    created = create_price_list(admin, company)
    url = f"/api/v1/price-lists/{created['id']}"

    response = admin.put(url, json={**price_list_update_body(created), "currency_code": "USD"})
    assert response.status_code == 422 and code_of(response) == "IMMUTABLE_FIELD"

    response = admin.put(url, json=price_list_update_body(
        created, valid_from="2026-10-05T00:00:00Z", valid_to="2026-10-01T00:00:00Z"
    ))
    assert response.status_code == 422 and code_of(response) == "VALIDITY_INVALID"

    response = admin.post(URL.format(company=company), json={"code": "X", "name": "X", "currency_code": "ZAR"})
    assert response.status_code == 422 and code_of(response) == "CURRENCY_NOT_SUPPORTED"


def test_deactivate_clears_default_and_marks_require_active(admin, company):
    created = create_price_list(admin, company, is_default=True)
    url = f"/api/v1/price-lists/{created['id']}"

    deactivated = admin.post(url + "/deactivate", json={"version": 1}).json()
    assert deactivated["status"] == "INACTIVE" and deactivated["is_default"] is False

    marked = admin.put(url, json=price_list_update_body(deactivated, is_default=True))
    assert marked.status_code == 422 and code_of(marked) == "DEFAULT_REQUIRES_ACTIVE"

    renamed = admin.put(url, json=price_list_update_body(deactivated, name="Renombrada"))
    assert renamed.status_code == 200 and renamed.json()["status"] == "INACTIVE"

    reactivated = admin.post(url + "/reactivate", json={"version": renamed.json()["version"]})
    assert reactivated.status_code == 200 and reactivated.json()["is_default"] is False


def test_list_filters(admin, company):
    create_price_list(admin, company, code="MINORISTA", name="Minorista", is_default=True)
    create_price_list(admin, company, code="EXPORT", name="Exportación", currency_code="USD")
    url = URL.format(company=company)

    assert admin.get(url).json()["total_records"] == 2
    assert admin.get(url, params={"currency_code": "usd"}).json()["total_records"] == 1
    assert admin.get(url, params={"is_default": "true"}).json()["items"][0]["code"] == "MINORISTA"
    assert admin.get(url, params={"search": "export"}).json()["total_records"] == 1


def test_permissions(as_user, admin, company):
    created = create_price_list(admin, company)
    assert as_user("consulta.test").get(f"/api/v1/price-lists/{created['id']}").status_code == 200
    assert as_user("ventas.test").post(URL.format(company=company), json={}).status_code == 403
    assert as_user("supervisor.test").post(
        f"/api/v1/price-lists/{created['id']}/deactivate", json={"version": 1}
    ).status_code == 403
    assert as_user("inventario.test").get(URL.format(company=company)).status_code == 403
