"""Reglas comerciales del MVP en ventas (spec 020; FR-020-09, FR-020-13; RC-MVP-3, RC-MVP-4, RC-MVP-6)."""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.conftest import base, count_rows, fetch, line, sale_body


def first_error(response) -> dict:
    return response.json()["errors"][0]


# ------------------------------------------------------------------ descuentos


def test_discount_is_rejected_when_creating_and_adding_lines(seller, world, make_draft, test_engine) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product, discount_amount="1")))
    assert response.status_code == 422
    assert first_error(response)["code"] == "DISCOUNT_NOT_ALLOWED" and first_error(response)["field"] == "lines[0].discount_amount"
    draft = make_draft(line(world.product))
    added = seller.post(f"{base(world)}/sales/{draft['id']}/details", json={**line(world.product_2, discount_amount="0.01"), "version": 1})
    assert added.status_code == 422 and first_error(added)["code"] == "DISCOUNT_NOT_ALLOWED"
    assert count_rows(test_engine, "sale_details") == 1


def test_zero_or_omitted_discount_keeps_the_list_price(seller, world) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product, "2", discount_amount="0"), line(world.product_2)))
    assert response.status_code == 201, response.text
    first, second = response.json()["lines"]
    assert first["discount_amount"] == second["discount_amount"] == "0.00"
    assert first["total"] == first["subtotal"]


def test_seller_cannot_alter_the_price_through_other_fields(seller, world) -> None:
    for extra in ({"unit_price": "1"}, {"subtotal": "1"}, {"total": "1"}, {"discount_percentage": "10"}):
        response = seller.post(f"{base(world)}/sales", json=sale_body(world, {**line(world.product), **extra}))
        assert response.status_code == 422, extra


def test_database_rejects_a_discount(world, make_draft, test_engine) -> None:
    draft = make_draft(line(world.product))
    with pytest.raises(Exception, match="ck_sale_details_no_discount"):
        with test_engine.begin() as connection:
            connection.execute(
                text("UPDATE sale_details SET discount_amount = 1, total = total - 1 WHERE sale_id = :id"), {"id": draft["id"]}
            )


# ----------------------------------------------------------------- medio de pago


def test_payment_method_is_required(seller, world) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product), payment_method_id=None))
    assert response.status_code == 422 and first_error(response)["field"] == "payment_method_id"


def test_payment_method_must_exist_and_be_active(seller, world, test_engine) -> None:
    missing = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product), payment_method_id=uuid4()))
    assert missing.status_code == 422 and first_error(missing)["code"] == "PAYMENT_METHOD_NOT_FOUND"
    inactive = seller.post(
        f"{base(world)}/sales", json=sale_body(world, line(world.product), payment_method_id=world.inactive_payment_method)
    )
    assert inactive.status_code == 409 and first_error(inactive)["code"] == "PAYMENT_METHOD_INACTIVE"
    assert count_rows(test_engine, "sales") == 0


def test_payment_method_is_revalidated_and_frozen_at_confirmation(seller, world, fakes, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft(line(world.product))
    fakes.pr.methods[world.payment_method] = replace(fakes.pr.methods[world.payment_method], status="INACTIVE")
    rejected = confirm(draft)
    assert rejected.status_code == 409 and first_error(rejected)["code"] == "PAYMENT_METHOD_INACTIVE"
    fakes.pr.methods[world.payment_method] = replace(fakes.pr.methods[world.payment_method], status="ACTIVE", name="Efectivo (caja)")
    confirmed = confirm(draft)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["payment_method_name_snapshot"] == "Efectivo (caja)"
    fakes.pr.methods[world.payment_method] = replace(fakes.pr.methods[world.payment_method], name="Otro")
    again = seller.get(f"{base(world)}/sales/{draft['id']}").json()
    assert again["payment_method_name_snapshot"] == "Efectivo (caja)"  # congelado (RC-MVP-4)


def test_only_one_payment_method_field_and_still_cash_only(seller, world) -> None:
    response = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product), payment_methods=[str(world.payment_method)]))
    assert response.status_code == 422
    credit = seller.post(f"{base(world)}/sales", json=sale_body(world, line(world.product), customer_payment_condition_id=uuid4()))
    assert credit.status_code == 422 and first_error(credit)["code"] == "PAYMENT_CONDITION_NOT_ALLOWED"


def test_payment_method_creates_no_financial_records(world, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    confirm(make_draft(line(world.product)))
    tables = {row["table_name"] for row in fetch(test_engine, "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")}
    assert not {name for name in tables if "payment" in name or "receivable" in name or "payable" in name}


def test_database_requires_the_method_outside_draft(world, make_draft, test_engine) -> None:
    draft = make_draft(line(world.product))
    with pytest.raises(Exception, match="ck_sales_payment_method"):
        with test_engine.begin() as connection:
            connection.execute(
                text("UPDATE sales SET payment_method_id = NULL, payment_method_code_snapshot = NULL WHERE id = :id"),
                {"id": draft["id"]},
            )
