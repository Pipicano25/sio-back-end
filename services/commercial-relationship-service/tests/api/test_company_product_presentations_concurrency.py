"""Concurrencia de presentaciones (T025; RC-04, RC-05, RC-07; SC-005, SC-006)."""

from __future__ import annotations

from tests.api.concurrency import race
from tests.api.helpers import adopt, adopt_presentation, global_presentation, presentation_update_body

URL = "/api/v1/companies/{company}/company-product-presentations"


def test_two_simultaneous_adoptions_of_the_same_presentation(app, user_token, as_user, company, fake_catalog):
    admin = as_user("admin.test")
    product = adopt(admin, company, fake_catalog)
    presentation = str(global_presentation(fake_catalog, product))
    body = {"company_product_id": product["id"], "global_product_presentation_id": presentation}

    results = race(app, user_token("admin.test"), [("POST", URL.format(company=company), body)] * 2)

    assert sorted(response.status_code for response in results) == [201, 409], [r.text for r in results]
    conflict = next(response for response in results if response.status_code == 409)
    assert conflict.json()["code"] == "COMMERCIAL_RELATIONSHIP.DUPLICATE_PRESENTATION_ADOPTION"
    # Según el entrelazado, la rechazada pudo registrar el primer uso (idempotente en
    # Product Catalog) o detenerse antes en la unicidad local; nunca hay inconsistencia.
    assert 1 <= len(fake_catalog.presentation_first_use_calls) <= 2
    assert admin.get(URL.format(company=company), params={"status": "ALL"}).json()["total_records"] == 1


def test_two_simultaneous_default_marks_leave_exactly_one(app, user_token, as_user, company, fake_catalog):
    admin = as_user("admin.test")
    product = adopt(admin, company, fake_catalog)
    first = adopt_presentation(admin, company, fake_catalog, product)
    second = adopt_presentation(admin, company, fake_catalog, product)

    results = race(
        app,
        user_token("admin.test"),
        [
            ("PUT", f"/api/v1/company-product-presentations/{row['id']}", presentation_update_body(row, is_default_purchase=True))
            for row in (first, second)
        ],
    )

    assert all(response.status_code in {200, 409} for response in results), [r.text for r in results]
    assert any(response.status_code == 200 for response in results)
    rows = admin.get(URL.format(company=company), params={"company_product_id": product["id"]}).json()["items"]
    assert sum(row["is_default_purchase"] for row in rows) == 1
