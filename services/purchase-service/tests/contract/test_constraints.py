"""Restricciones de la base (data-model.md; RC-02, RC-03; T011)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from tests.contract.db_rows import confirmed_overrides, insert_detail, insert_operation, insert_purchase, insert_sequence


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
        purchase = insert_purchase(connection)
        insert_detail(connection, purchase)
        insert_purchase(connection, **confirmed_overrides(sequence))
        insert_purchase(connection, status="CANCELLED", cancelled_by_user_id=uuid4(), cancelled_at="2026-10-06T00:00:00Z", cancellation_reason="x")


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "CONFIRMED"},  # sin número ni entrada
        {"number": "CP-1"},  # DRAFT con número
        {"inventory_operation_id": uuid4()},  # DRAFT con operación de Inventory
        {"status": "CANCELLED"},  # sin datos de anulación
        {"cancellation_reason": "x"},  # DRAFT con motivo
    ],
)
def test_lifecycle(engine, overrides) -> None:
    rejects(engine, lambda c: insert_purchase(c, **overrides), "ck_purchases_lifecycle")


def test_confirmed_requires_inventory_operation(engine) -> None:
    with engine.begin() as connection:
        sequence = insert_sequence(connection)
    rejects(
        engine,
        lambda c: insert_purchase(c, **{**confirmed_overrides(sequence), "inventory_operation_id": None}),
        "ck_purchases_lifecycle",
    )


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"total": 5}, "ck_purchases_totals"),
        ({"due_date": "2026-10-05"}, "ck_purchases_due_date"),
        ({"payment_terms_days_snapshot": 30}, "ck_purchases_payment_terms"),  # CASH con plazo
        ({"payment_condition_code_snapshot": "OTRO"}, "ck_purchases_payment_code"),
        ({"currency_code": "co"}, "ck_purchases_currency_code"),
        ({"status": "OTRO"}, "ck_purchases_"),  # viola ck_purchases_status y ck_purchases_lifecycle
    ],
)
def test_purchase_checks(engine, overrides, constraint) -> None:
    rejects(engine, lambda c: insert_purchase(c, **overrides), constraint)


def test_number_unique_per_company(engine) -> None:
    company = uuid4()
    with engine.begin() as connection:
        sequence = insert_sequence(connection, company_id=company)
        insert_purchase(connection, company_id=company, **{**confirmed_overrides(sequence), "number": "CP-000001"})
        # Otra empresa puede repetir el número.
        insert_purchase(connection, **{**confirmed_overrides(sequence), "number": "CP-000001"})
    rejects(
        engine,
        lambda c: insert_purchase(c, company_id=company, **{**confirmed_overrides(sequence), "number": "CP-000001"}),
        "uq_purchases_company_number",
    )


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"line_number": 0}, "ck_purchase_details_line_number"),
        ({"line_number": 101}, "ck_purchase_details_line_number"),
        ({"quantity": 0}, "ck_purchase_details_quantity"),
        ({"discount_amount": 11}, "ck_purchase_details_discount_amount"),
        ({"total": 9}, "ck_purchase_details_total"),
        ({"base_quantity_factor_snapshot": 12}, "ck_purchase_details_presentation"),  # factor ≠ 1 sin presentación
        ({"company_product_presentation_id": uuid4()}, "ck_purchase_details_presentation"),  # sin snapshots
        ({"base_quantity_factor_snapshot": 0}, "ck_purchase_details_factor"),
    ],
)
def test_detail_checks(engine, overrides, constraint) -> None:
    with engine.begin() as connection:
        purchase = insert_purchase(connection)
    rejects(engine, lambda c: insert_detail(c, purchase, **overrides), constraint)


def test_line_number_unique_per_purchase(engine) -> None:
    with engine.begin() as connection:
        purchase = insert_purchase(connection)
        insert_detail(connection, purchase)
    rejects(engine, lambda c: insert_detail(c, purchase), "uq_purchase_details_line_number")


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"document_kind": "SALE"}, "ck_purchase_sequences_document_kind"),
        ({"prefix": "cp"}, "ck_purchase_sequences_prefix"),
        ({"separator": "#"}, "ck_purchase_sequences_separator"),
        ({"maximum_number": 0, "initial_number": 1}, "ck_purchase_sequences_maximum_number"),
        ({"number_length": 19}, "ck_purchase_sequences_number_length"),
        ({"reset_policy": "WEEKLY"}, "ck_purchase_sequences_reset_policy"),
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
    rejects(engine, lambda c: insert_sequence(c, company_id=company, series_code="C"), "uq_purchase_sequences_active")
    rejects(engine, lambda c: insert_sequence(c, company_id=company, series_code="A", is_active=False), "uq_purchase_sequences_series")


def test_counter_period_key(engine) -> None:
    from sqlalchemy import text

    with engine.begin() as connection:
        sequence = insert_sequence(connection)
    for period in ("2026", "202610", ""):
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO purchase_sequence_counters (purchase_sequence_id, period_key, current_number, created_by, updated_by) VALUES (:s, :p, 1, 'x', 'x')"),
                {"s": sequence, "p": period},
            )
    rejects(
        engine,
        lambda c: c.execute(
            text("INSERT INTO purchase_sequence_counters (purchase_sequence_id, period_key, current_number, created_by, updated_by) VALUES (:s, '20261', 1, 'x', 'x')"),
            {"s": sequence},
        ),
        "ck_purchase_sequence_counters_period_key",
    )


def test_operation_checks(engine) -> None:
    with engine.begin() as connection:
        company = uuid4()
        purchase = insert_purchase(connection, company_id=company)
        insert_operation(connection, purchase, company)
    rejects(engine, lambda c: insert_operation(c, purchase, company), "uq_purchase_operations_pending")
    rejects(
        engine,
        lambda c: insert_operation(c, purchase, company, status="FAILED", completed_at="2026-10-06T00:00:00Z"),
        "ck_purchase_operations_failed_code",
    )
    rejects(engine, lambda c: insert_operation(c, purchase, company, status="SUCCEEDED"), "ck_purchase_operations_completed_at")
    rejects(
        engine,
        lambda c: insert_operation(c, purchase, company, status="SUCCEEDED", completed_at="2026-10-06T00:00:00Z"),
        "ck_purchase_operations_inventory_operation",
    )
    rejects(  # D-02: una anulación siempre guarda su motivo
        engine,
        lambda c: insert_operation(c, purchase, company, operation_type="CANCEL", reason=None, status="FAILED",
                                   error_code="X", completed_at="2026-10-06T00:00:00Z"),
        "ck_purchase_operations_cancel_reason",
    )
    with engine.begin() as connection:  # CANCEL de un DRAFT: SUCCEEDED sin operación de Inventory
        insert_operation(
            connection, purchase, company, operation_type="CANCEL", status="SUCCEEDED", completed_at="2026-10-06T00:00:00Z"
        )


def test_idempotency_key_globally_unique(engine) -> None:
    with engine.begin() as connection:
        company = uuid4()
        purchase = insert_purchase(connection, company_id=company)
        insert_operation(connection, purchase, company, idempotency_key="k-1", status="FAILED", error_code="X", completed_at="2026-10-06T00:00:00Z")
    rejects(engine, lambda c: insert_operation(c, purchase, company, idempotency_key="k-1"), "uq_purchase_operations_idempotency_key")


def test_lifecycle_event_checks(engine) -> None:
    from sqlalchemy import text

    with engine.begin() as connection:
        purchase = insert_purchase(connection)
    rejects(
        engine,
        lambda c: c.execute(
            text(
                "INSERT INTO purchase_lifecycle_events (id, company_id, purchase_id, event_type, occurred_at, "
                "recorded_by_user_id, source, created_by) VALUES (:id, :c, :p, 'SHIPPED', now(), :u, 'USER', 'x')"
            ),
            {"id": uuid4(), "c": uuid4(), "p": purchase, "u": uuid4()},
        ),
        "ck_purchase_lifecycle_events_event_type",
    )
