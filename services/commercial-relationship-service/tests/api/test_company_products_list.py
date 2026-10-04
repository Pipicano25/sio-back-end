"""Historia 2: listado de productos de una empresa (FR-017, FR-005, R-13)."""

from __future__ import annotations

from uuid import uuid4

from tests.api.helpers import adopt
from tests.conftest import user_sub

URL = "/api/v1/companies/{company}/company-products"


def _list(client, company, **params):
    response = client.get(URL.format(company=company), params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_only_company_products_and_active_by_default(as_user, company, fake_catalog, fake_oc):
    client = as_user("admin.test")
    other = uuid4()
    fake_oc.add_member(user_sub("admin.test"), other)

    a = adopt(client, company, fake_catalog, internal_code="A", display_name="Bravo")
    b = adopt(client, company, fake_catalog, internal_code="B", display_name="Alfa")
    adopt(client, other, fake_catalog, internal_code="C", display_name="Otra empresa")
    client.post(f"/api/v1/company-products/{a['id']}/deactivate", json={"version": 1})

    page = _list(client, company)
    assert [item["id"] for item in page["items"]] == [b["id"]]
    assert page["total_records"] == 1 and page["total_pages"] == 1

    assert [item["id"] for item in _list(client, company, status="INACTIVE")["items"]] == [a["id"]]
    # Orden por display_name.
    assert [item["display_name"] for item in _list(client, company, status="ALL")["items"]] == ["Alfa", "Bravo"]


def test_filters(as_user, company, fake_catalog):
    client = as_user("admin.test")
    sellable = adopt(client, company, fake_catalog, internal_code="S", is_purchasable=False)
    purchasable = adopt(client, company, fake_catalog, internal_code="P", is_sellable=False)
    untracked = adopt(client, company, fake_catalog, internal_code="U", inventory_control_enabled=False)

    assert {i["id"] for i in _list(client, company, is_sellable="false")["items"]} == {purchasable["id"]}
    assert {i["id"] for i in _list(client, company, is_purchasable="false")["items"]} == {sellable["id"]}
    assert {i["id"] for i in _list(client, company, inventory_control_enabled="false")["items"]} == {untracked["id"]}
    assert [i["id"] for i in _list(client, company, global_product_id=sellable["global_product_id"])["items"]] == [
        sellable["id"]
    ]


def test_search_is_partial_case_insensitive_and_escaped(as_user, company, fake_catalog):
    client = as_user("admin.test")
    a = adopt(client, company, fake_catalog, internal_code="000045", display_name="Acetaminofén", reference_code="RF-1")
    b = adopt(client, company, fake_catalog, internal_code="022348", display_name="Leche NAN 100%")

    assert [i["id"] for i in _list(client, company, search="aceta")["items"]] == [a["id"]]
    assert [i["id"] for i in _list(client, company, search="0223")["items"]] == [b["id"]]
    assert [i["id"] for i in _list(client, company, search="rf-1")["items"]] == [a["id"]]
    assert [i["id"] for i in _list(client, company, search="100%")["items"]] == [b["id"]]
    assert [i["id"] for i in _list(client, company, search="%")["items"]] == [b["id"]]
    assert _list(client, company, search="_")["total_records"] == 0


def test_pagination(as_user, company, fake_catalog):
    client = as_user("admin.test")
    for index in range(5):
        adopt(client, company, fake_catalog, internal_code=f"P{index}", display_name=f"Producto {index}")

    page = _list(client, company, page=2, page_size=2)
    assert page["page"] == 2 and page["page_size"] == 2
    assert page["total_records"] == 5 and page["total_pages"] == 3
    assert [i["display_name"] for i in page["items"]] == ["Producto 2", "Producto 3"]

    assert client.get(URL.format(company=company), params={"page_size": 101}).status_code == 422
    assert client.get(URL.format(company=company), params={"status": "BLOCKED"}).status_code == 422


def test_inactive_company_still_readable(as_user, company, fake_catalog, fake_oc):
    adopt(as_user("admin.test"), company, fake_catalog)
    fake_oc.inactive_companies.add(company)
    assert _list(as_user("consulta.test"), company)["total_records"] == 1
