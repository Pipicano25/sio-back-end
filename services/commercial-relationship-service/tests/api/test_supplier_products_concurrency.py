"""Concurrencia de productos de proveedor (T034; RC-04, RC-05; SC-006)."""

from __future__ import annotations

from tests.api.concurrency import race
from tests.api.helpers import (
    adopt,
    create_supplier_product,
    supplier,
    supplier_product_body,
    supplier_product_update_body,
)

URL = "/api/v1/companies/{company}/supplier-products"


def test_two_simultaneous_identical_relations(app, user_token, as_user, company, fake_catalog, fake_party):
    admin = as_user("admin.test")
    product = adopt(admin, company, fake_catalog)
    provider = supplier(admin, company, fake_party)
    body = supplier_product_body(provider, product, fake_catalog)

    results = race(app, user_token("admin.test"), [("POST", URL.format(company=company), body)] * 2)

    assert sorted(response.status_code for response in results) == [201, 409], [r.text for r in results]
    conflict = next(response for response in results if response.status_code == 409)
    assert conflict.json()["code"] == "COMMERCIAL_RELATIONSHIP.DUPLICATE_SUPPLIER_PRODUCT"


def test_two_simultaneous_preferred_marks_leave_exactly_one(app, user_token, as_user, company, fake_catalog, fake_party):
    admin = as_user("admin.test")
    product = adopt(admin, company, fake_catalog)
    rows = [
        create_supplier_product(admin, company, supplier(admin, company, fake_party, internal_code=f"PRV-{i}"), product, fake_catalog)
        for i in range(2)
    ]

    results = race(
        app,
        user_token("admin.test"),
        [("PUT", f"/api/v1/supplier-products/{row['id']}", supplier_product_update_body(row, is_preferred=True)) for row in rows],
    )

    assert all(response.status_code in {200, 409} for response in results), [r.text for r in results]
    listed = admin.get(URL.format(company=company), params={"company_product_id": product["id"]}).json()["items"]
    assert sum(row["is_preferred"] for row in listed) == 1
