"""Concurrencia de la condición predeterminada por moneda (T043; RC-05; SC-006)."""

from __future__ import annotations

from tests.api.concurrency import race
from tests.api.helpers import condition_update_body, create_condition, supplier

URL = "/api/v1/companies/{company}/supplier-payment-conditions"


def test_two_simultaneous_defaults_same_currency_leave_one(app, user_token, as_user, company, fake_party, fake_payment):
    admin = as_user("admin.test")
    provider = supplier(admin, company, fake_party)
    rows = [create_condition(admin, company, provider, fake_payment) for _ in range(2)]

    results = race(
        app,
        user_token("admin.test"),
        [("PUT", f"/api/v1/supplier-payment-conditions/{row['id']}", condition_update_body(row, is_default=True)) for row in rows],
    )

    assert all(response.status_code in {200, 409} for response in results), [r.text for r in results]
    listed = admin.get(URL.format(company=company)).json()["items"]
    assert sum(row["is_default"] for row in listed) == 1


def test_defaults_in_different_currencies_coexist(app, user_token, as_user, company, fake_party, fake_payment):
    admin = as_user("admin.test")
    provider = supplier(admin, company, fake_party)
    rows = [
        create_condition(admin, company, provider, fake_payment, currency_code=currency) for currency in ("COP", "USD")
    ]

    results = race(
        app,
        user_token("admin.test"),
        [("PUT", f"/api/v1/supplier-payment-conditions/{row['id']}", condition_update_body(row, is_default=True)) for row in rows],
    )

    assert [response.status_code for response in results] == [200, 200]
    listed = admin.get(URL.format(company=company)).json()["items"]
    assert sum(row["is_default"] for row in listed) == 2
