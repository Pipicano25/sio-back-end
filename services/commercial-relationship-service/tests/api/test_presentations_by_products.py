"""CR-2: presentaciones de varios productos en una llamada (spec 022, FR-022-81; T015)."""

from __future__ import annotations

from uuid import uuid4

from tests.api.helpers import adopt, adopt_presentation
from tests.conftest import LOOKUP

URL = "/api/v1/companies/{company}/company-product-presentations/by-products"
READ = "perm:commercial-relationship:company_product_presentations:read"


def test_returns_all_presentations_of_the_products_in_stable_order(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    first = adopt(client, company, fake_catalog, internal_code="P1")
    second = adopt(client, company, fake_catalog, internal_code="P2")
    other = adopt(client, company, fake_catalog, internal_code="P3")
    created = [
        adopt_presentation(client, company, fake_catalog, first, sku="S-1A", internal_code="I-1A"),
        adopt_presentation(client, company, fake_catalog, first, sku="S-1B"),
        adopt_presentation(client, company, fake_catalog, second, sku="S-2A", reference_code="R-2A"),
    ]
    adopt_presentation(client, company, fake_catalog, other, sku="S-3A")

    response = client.post(URL.format(company=company), json={"company_product_ids": [second["id"], first["id"], first["id"]]})
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    expected = sorted(created, key=lambda p: (p["company_product_id"], p["id"]))
    assert [item["id"] for item in items] == [p["id"] for p in expected]
    by_id = {item["id"]: item for item in items}
    assert by_id[created[0]["id"]]["sku"] == "S-1A"
    assert by_id[created[0]["id"]]["internal_code"] == "I-1A"
    assert by_id[created[2]["id"]]["reference_code"] == "R-2A"
    assert {"company_id", "global_product_presentation_id", "is_sellable", "status", "version"} <= set(items[0])


def test_status_filter(as_user, company, fake_catalog) -> None:
    client = as_user("admin.test")
    product = adopt(client, company, fake_catalog, internal_code="P1")
    active = adopt_presentation(client, company, fake_catalog, product, sku="S-A")
    inactive = adopt_presentation(client, company, fake_catalog, product, sku="S-I")
    client.post(f"/api/v1/company-product-presentations/{inactive['id']}/deactivate", json={"version": 1})

    def ids(status: str | None) -> set[str]:
        body = {"company_product_ids": [product["id"]], **({"status": status} if status else {})}
        return {item["id"] for item in client.post(URL.format(company=company), json=body).json()["items"]}

    assert ids(None) == {active["id"], inactive["id"]}
    assert ids("ACTIVE") == {active["id"]}
    assert ids("INACTIVE") == {inactive["id"]}


def test_products_of_another_company_are_absent(as_user, fake_oc, company, other_company, fake_catalog) -> None:
    client = as_user("admin.test")
    from tests.conftest import user_sub

    fake_oc.add_member(user_sub("admin.test"), other_company)
    foreign = adopt(client, other_company, fake_catalog, internal_code="F1")
    adopt_presentation(client, other_company, fake_catalog, foreign, sku="S-F")

    response = client.post(URL.format(company=company), json={"company_product_ids": [foreign["id"]]})
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_limits_and_permissions(as_user, as_token, service_token, company, other_company) -> None:
    client = as_user("admin.test")
    url = URL.format(company=company)
    assert client.post(url, json={"company_product_ids": [str(uuid4()) for _ in range(101)]}).status_code == 422
    assert client.post(url, json={"company_product_ids": []}).status_code == 422
    assert client.post(url, json={"company_product_ids": [str(uuid4())], "extra": 1}).status_code == 422
    assert as_user("inventario.test").post(url, json={"company_product_ids": [str(uuid4())]}).status_code == 403
    assert client.post(URL.format(company=other_company), json={"company_product_ids": [str(uuid4())]}).status_code == 404

    technical = as_token(service_token(READ, LOOKUP, client_id="product-inventory-query-service"))
    assert technical.post(url, json={"company_product_ids": [str(uuid4())]}).status_code == 200
