"""Reglas comerciales del MVP en compras (spec 020; FR-020-08, FR-020-09, FR-020-11, FR-020-12; RC-MVP-3..5)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from purchase_service.application.ports import GlobalPresentationInfo
from tests.conftest import base, count_rows, fetch, line, purchase_body


def create(buyer, world, *lines, **header):
    return buyer.post(f"{base(world)}/purchases", json=purchase_body(world, *lines, **header))


def first_error(response) -> dict:
    return response.json()["errors"][0]


# ---------------------------------------------------------------- solo contado


@pytest.mark.parametrize("condition", ["credit_condition", "financing_condition"])
def test_credit_and_financing_are_not_available(buyer, world, test_engine, condition) -> None:
    response = create(buyer, world, line(world.product), supplier_payment_condition_id=getattr(world, condition))
    assert response.status_code == 409
    assert response.json()["code"] == "PURCHASE.REFERENCES_NOT_ELIGIBLE"
    error = first_error(response)
    assert error["code"] == "PAYMENT_CONDITION_NOT_AVAILABLE" and error["field"] == "supplier_payment_condition_id"
    assert "solo se admiten compras de contado" in error["message"]
    assert count_rows(test_engine, "purchases") == 0


def test_header_edit_cannot_switch_to_credit(buyer, world, make_draft) -> None:
    draft = make_draft()
    body = {
        "branch_id": draft["branch_id"],
        "company_supplier_id": draft["company_supplier_id"],
        "operation_date": draft["operation_date"],
        "payment_method_id": draft["payment_method_id"],
        "supplier_payment_condition_id": str(world.credit_condition),
        "version": draft["version"],
    }
    response = buyer.put(f"{base(world)}/purchases/{draft['id']}", json=body)
    assert response.status_code == 409 and first_error(response)["code"] == "PAYMENT_CONDITION_NOT_AVAILABLE"


def test_database_rejects_a_non_cash_purchase(world, make_draft, test_engine) -> None:
    """RC-MVP-3: también en la base (`ck_purchases_cash_only`)."""
    draft = make_draft()
    with pytest.raises(Exception, match="ck_purchases_cash_only"):
        with test_engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE purchases SET payment_condition_code_snapshot = 'CREDIT', payment_terms_days_snapshot = 30, "
                    "due_date = operation_date + 30 WHERE id = :id"
                ),
                {"id": draft["id"]},
            )


# ----------------------------------------------------------------- medio de pago


def test_payment_method_is_required(buyer, world) -> None:
    response = create(buyer, world, line(world.product), payment_method_id=None)
    assert response.status_code == 422 and first_error(response)["field"] == "payment_method_id"


def test_payment_method_must_exist_and_be_active(buyer, world, test_engine) -> None:
    missing = create(buyer, world, line(world.product), payment_method_id=uuid4())
    assert missing.status_code == 422 and first_error(missing)["code"] == "PAYMENT_METHOD_NOT_FOUND"
    inactive = create(buyer, world, line(world.product), payment_method_id=world.inactive_payment_method)
    assert inactive.status_code == 409 and first_error(inactive)["code"] == "PAYMENT_METHOD_INACTIVE"
    assert count_rows(test_engine, "purchases") == 0


def test_only_one_payment_method_field_exists(buyer, world) -> None:
    response = create(buyer, world, line(world.product), payment_methods=[str(world.payment_method)])
    assert response.status_code == 422 and first_error(response)["code"] == "UNKNOWN_FIELD"


def test_payment_method_is_stored_without_financial_records(buyer, world, make_sequence, make_draft, confirm, test_engine) -> None:
    """El medio de pago es declarativo: no crea pagos, abonos ni saldos (no existen tablas para ello)."""
    make_sequence()
    confirmed = confirm(make_draft()).json()
    stored = fetch(test_engine, "SELECT payment_method_id, payment_method_code_snapshot FROM purchases")[0]
    assert str(stored["payment_method_id"]) == confirmed["payment_method_id"] == str(world.payment_method)
    tables = {row["table_name"] for row in fetch(test_engine, "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")}
    assert not {name for name in tables if "payment" in name or "receivable" in name or "payable" in name}


# ------------------------------------------------------------------ presentación


def test_line_without_presentation_is_422(buyer, world, test_engine) -> None:
    response = create(buyer, world, line(world.product, company_product_presentation_id=None))
    assert response.status_code == 422
    assert first_error(response)["field"] == "lines[0].company_product_presentation_id"
    assert count_rows(test_engine, "purchases") == 0


def test_unit_purchase_uses_the_factor_one_presentation(buyer, world) -> None:
    response = create(buyer, world, line(world.product, "5", "800"))
    assert response.status_code == 201, response.text
    detail = response.json()["lines"][0]
    assert detail["base_quantity_factor_snapshot"] == "1.00000000" and detail["base_quantity"] == "5.0000"
    assert detail["inventory_unit_cost"] == "800.0000"


def test_database_rejects_a_line_without_presentation(world, make_draft, test_engine) -> None:
    draft = make_draft()
    with pytest.raises(Exception, match="ck_purchase_details_presentation"):
        with test_engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE purchase_details SET company_product_presentation_id = NULL, presentation_code_snapshot = NULL, "
                    "presentation_name_snapshot = NULL WHERE purchase_id = :id"
                ),
                {"id": draft["id"]},
            )


# ---------------------------------------------------------------------- costos


def test_base_unit_cost_rounding_to_zero_is_rejected(buyer, world, fakes) -> None:
    """0,01 por una caja de 1 000 unidades: 0,00001 por unidad base redondea a 0,0000."""
    fakes.catalog.presentations[world.global_presentation] = GlobalPresentationInfo(
        world.global_presentation, "CAJA1000", "Caja x1000", Decimal("1000")
    )
    response = create(buyer, world, line(world.product, "1", "0.01", company_product_presentation_id=world.presentation))
    assert response.status_code == 422
    error = first_error(response)
    assert error["code"] == "BASE_UNIT_COST_NOT_POSITIVE" and error["field"] == "lines[0].unit_cost"


def test_line_edit_rechecks_costs(buyer, world, make_draft) -> None:
    draft = make_draft()
    detail = draft["lines"][0]
    response = buyer.put(
        f"{base(world)}/purchases/{draft['id']}/details/{detail['id']}",
        json={**line(world.product, "2", "1000", discount_amount="2000"), "version": draft["version"]},
    )
    assert response.status_code == 422 and first_error(response)["code"] == "NET_COST_NOT_POSITIVE"


def test_database_rejects_zero_cost_lines(world, make_draft, test_engine) -> None:
    draft = make_draft()
    for statement, constraint in (
        ("UPDATE purchase_details SET unit_cost = 0 WHERE purchase_id = :id", "ck_purchase_details_unit_cost"),
        ("UPDATE purchase_details SET discount_amount = subtotal, total = tax_amount WHERE purchase_id = :id", "ck_purchase_details_net_cost"),
    ):
        with pytest.raises(Exception, match=constraint):
            with test_engine.begin() as connection:
                connection.execute(text(statement), {"id": draft["id"]})
