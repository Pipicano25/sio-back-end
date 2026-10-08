"""Restricciones de la base (data-model.md; RC-02, RC-03, DP-01, P-01, P-02, C-03; T013)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from tests.contract.db_rows import confirmed_overrides, insert_detail, insert_operation, insert_sale, insert_sequence


def rejects(test_engine, action, constraint: str) -> None:
    with pytest.raises(IntegrityError) as error, test_engine.begin() as connection:
        action(connection)
    assert constraint in str(error.value)


@pytest.fixture
def engine(test_engine, clean_database):
    return test_engine


def test_valid_rows_are_accepted(engine) -> None:
    with engine.begin() as connection:
        sequence = insert_sequence(connection)
        sale = insert_sale(connection)
        insert_detail(connection, sale)
        insert_sale(connection, **confirmed_overrides(sequence))
        insert_sale(connection, status="CANCELLED", cancelled_by_user_id=uuid4(), cancelled_at="2026-10-06T00:00:00Z", cancellation_reason="x")


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "CONFIRMED"},  # sin número ni entrada
        {"number": "FV-1"},  # DRAFT con número
        {"inventory_operation_id": uuid4()},  # DRAFT con operación de Inventory
        {"status": "CANCELLED"},  # sin datos de anulación
        {"cancellation_reason": "x"},  # DRAFT con motivo
    ],
)
def test_lifecycle(engine, overrides) -> None:
    rejects(engine, lambda c: insert_sale(c, **overrides), "ck_sales_lifecycle")


def test_confirmed_requires_inventory_operation(engine) -> None:
    with engine.begin() as connection:
        sequence = insert_sequence(connection)
    rejects(
        engine,
        lambda c: insert_sale(c, **{**confirmed_overrides(sequence), "inventory_operation_id": None}),
        "ck_sales_lifecycle",
    )


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"total": 5}, "ck_sales_totals"),
        ({"due_date": "2026-11-05"}, "ck_sales_cash_only"),  # DP-01: due_date = operation_date
        ({"payment_terms_days_snapshot": 30}, "ck_sales_"),  # contado sin plazo
        ({"payment_condition_code_snapshot": "CREDIT"}, "ck_sales_cash_only"),
        ({"customer_payment_condition_id": uuid4()}, "ck_sales_cash_only"),
        ({"payment_condition_code_snapshot": "OTRO"}, "ck_sales_"),
        ({"has_unknown_cost": True}, "ck_sales_draft_unknown_cost"),
        ({"currency_code": "co"}, "ck_sales_currency_code"),
        ({"status": "OTRO"}, "ck_sales_"),  # viola ck_sales_status y ck_sales_lifecycle
    ],
)
def test_sale_checks(engine, overrides, constraint) -> None:
    rejects(engine, lambda c: insert_sale(c, **overrides), constraint)


def test_number_unique_per_company(engine) -> None:
    company = uuid4()
    with engine.begin() as connection:
        sequence = insert_sequence(connection, company_id=company)
        insert_sale(connection, company_id=company, **{**confirmed_overrides(sequence), "number": "FV-000001"})
        # Otra empresa puede repetir el número.
        insert_sale(connection, **{**confirmed_overrides(sequence), "number": "FV-000001"})
    rejects(
        engine,
        lambda c: insert_sale(c, company_id=company, **{**confirmed_overrides(sequence), "number": "FV-000001"}),
        "uq_sales_company_number",
    )


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"line_number": 0}, "ck_sale_details_line_number"),
        ({"line_number": 101}, "ck_sale_details_line_number"),
        ({"quantity": 0}, "ck_sale_details_quantity"),
        ({"discount_amount": 11}, "ck_sale_details_discount_amount"),
        ({"total": 9}, "ck_sale_details_total"),
        ({"base_quantity_factor_snapshot": 12}, "ck_sale_details_presentation"),  # factor ≠ 1 sin presentación
        ({"company_product_presentation_id": uuid4()}, "ck_sale_details_presentation"),  # sin snapshots
        ({"base_quantity_factor_snapshot": 0}, "ck_sale_details_factor"),
        ({"unit_price": -1}, "ck_sale_details_unit_price"),
        ({"price_list_item_id": uuid4()}, "ck_sale_details_price_list_item"),  # ítem sin lista
        ({"price_list_requested": True}, "ck_sale_details_price_list_requested"),  # P-02: pedida sin lista
        ({"unit_cost_snapshot": 5}, "ck_sale_details_cost_block"),  # costo incompleto
        ({"unit_cost_snapshot": 5, "cost_total": 5, "cost_known": True}, "ck_sale_details_margin_amount"),
        ({"unit_cost_snapshot": 5, "cost_total": 5, "cost_known": False, "gross_margin_amount": 5},
         "ck_sale_details_margin_amount"),  # C-03: costo desconocido sin margen
        ({"gross_margin_amount": 1}, "ck_sale_details_margin_amount"),  # margen sin costo
        ({"unit_cost_snapshot": 5, "cost_total": 5, "cost_known": True, "gross_margin_amount": 5,
          "gross_margin_percentage": 100.0001}, "ck_sale_details_margin_percentage"),
        ({"unit_cost_snapshot": -1, "cost_total": 5, "cost_known": True, "gross_margin_amount": 5},
         "ck_sale_details_unit_cost_snapshot"),
    ],
)
def test_detail_checks(engine, overrides, constraint) -> None:
    with engine.begin() as connection:
        sale = insert_sale(connection)
    rejects(engine, lambda c: insert_detail(c, sale, **overrides), constraint)


def test_cost_and_margin_rows_that_are_valid(engine) -> None:
    """Costo conocido con porcentaje nulo (P-01) y costo desconocido sin margen (C-03)."""
    with engine.begin() as connection:
        sale = insert_sale(connection)
        insert_detail(connection, sale, line_number=1, unit_cost_snapshot=5, cost_total=5, cost_known=True,
                      gross_margin_amount=-5, gross_margin_percentage=None)
        insert_detail(connection, sale, line_number=2, unit_cost_snapshot=0, cost_total=0, cost_known=False)
        insert_detail(connection, sale, line_number=3, unit_cost_snapshot=5, cost_total=5, cost_known=True,
                      gross_margin_amount=5, gross_margin_percentage=-999.9999)
        insert_detail(connection, sale, line_number=4, price_list_id=uuid4(), price_list_item_id=uuid4(),
                      price_list_requested=True)


def test_line_number_unique_per_sale(engine) -> None:
    with engine.begin() as connection:
        sale = insert_sale(connection)
        insert_detail(connection, sale)
    rejects(engine, lambda c: insert_detail(c, sale), "uq_sale_details_line_number")


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"document_kind": "PURCHASE"}, "ck_sale_sequences_document_kind"),
        ({"prefix": "fv"}, "ck_sale_sequences_prefix"),
        ({"separator": "#"}, "ck_sale_sequences_separator"),
        ({"maximum_number": 0, "initial_number": 1}, "ck_sale_sequences_maximum_number"),
        ({"number_length": 19}, "ck_sale_sequences_number_length"),
        ({"reset_policy": "WEEKLY"}, "ck_sale_sequences_reset_policy"),
    ],
)
def test_sequence_checks(engine, overrides, constraint) -> None:
    rejects(engine, lambda c: insert_sequence(c, **overrides), constraint)


def test_one_active_sequence_per_scope(engine) -> None:
    company, branch = uuid4(), uuid4()
    with engine.begin() as connection:
        insert_sequence(connection, company_id=company, series_code="A")
        insert_sequence(connection, company_id=company, branch_id=branch, series_code="A")  # otro alcance
        insert_sequence(connection, company_id=company, series_code="B", is_active=False)
    rejects(engine, lambda c: insert_sequence(c, company_id=company, series_code="C"), "uq_sale_sequences_active")
    rejects(engine, lambda c: insert_sequence(c, company_id=company, series_code="A", is_active=False), "uq_sale_sequences_series")


def test_counter_period_key(engine) -> None:
    from sqlalchemy import text

    with engine.begin() as connection:
        sequence = insert_sequence(connection)
    for period in ("2026", "202610", ""):
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO sale_sequence_counters (sale_sequence_id, period_key, current_number, created_by, updated_by) VALUES (:s, :p, 1, 'x', 'x')"),
                {"s": sequence, "p": period},
            )
    rejects(
        engine,
        lambda c: c.execute(
            text("INSERT INTO sale_sequence_counters (sale_sequence_id, period_key, current_number, created_by, updated_by) VALUES (:s, '20261', 1, 'x', 'x')"),
            {"s": sequence},
        ),
        "ck_sale_sequence_counters_period_key",
    )


def test_operation_checks(engine) -> None:
    with engine.begin() as connection:
        company = uuid4()
        sale = insert_sale(connection, company_id=company)
        insert_operation(connection, sale, company)
    rejects(engine, lambda c: insert_operation(c, sale, company), "uq_sale_operations_pending")
    rejects(
        engine,
        lambda c: insert_operation(c, sale, company, status="FAILED", completed_at="2026-10-06T00:00:00Z"),
        "ck_sale_operations_failed_code",
    )
    rejects(engine, lambda c: insert_operation(c, sale, company, status="SUCCEEDED"), "ck_sale_operations_completed_at")
    rejects(
        engine,
        lambda c: insert_operation(c, sale, company, status="SUCCEEDED", completed_at="2026-10-06T00:00:00Z"),
        "ck_sale_operations_inventory_operation",
    )
    rejects(  # D-02: una anulación siempre guarda su motivo
        engine,
        lambda c: insert_operation(c, sale, company, operation_type="CANCEL", reason=None, status="FAILED",
                                   error_code="X", completed_at="2026-10-06T00:00:00Z"),
        "ck_sale_operations_cancel_reason",
    )
    with engine.begin() as connection:  # CANCEL de un DRAFT: SUCCEEDED sin operación de Inventory
        insert_operation(
            connection, sale, company, operation_type="CANCEL", status="SUCCEEDED", completed_at="2026-10-06T00:00:00Z"
        )


def test_idempotency_key_globally_unique(engine) -> None:
    with engine.begin() as connection:
        company = uuid4()
        sale = insert_sale(connection, company_id=company)
        insert_operation(connection, sale, company, idempotency_key="k-1", status="FAILED", error_code="X", completed_at="2026-10-06T00:00:00Z")
    rejects(engine, lambda c: insert_operation(c, sale, company, idempotency_key="k-1"), "uq_sale_operations_idempotency_key")
