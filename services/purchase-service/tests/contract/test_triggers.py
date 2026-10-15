"""Triggers de ciclo de vida e inmutabilidad (data-model.md; RC-03; T012)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.contract.db_rows import insert_detail, insert_operation, insert_purchase, insert_sequence


@pytest.fixture
def engine(test_engine, clean_database):
    return test_engine


def fails(engine, sql: str, params: dict, fragment: str = "") -> None:
    with pytest.raises(DBAPIError) as error, engine.begin() as connection:
        connection.execute(text(sql), params)
    assert fragment in str(error.value)


def setup_confirmed(engine, *, received: bool = True):
    """Compra confirmada; con `received`, además recibida (spec 020: la recepción aplica la entrada)."""
    with engine.begin() as connection:
        sequence = insert_sequence(connection)
        purchase = insert_purchase(connection)
        insert_detail(connection, purchase)
        connection.execute(
            text("UPDATE purchases SET status='CONFIRMED', number='CP-1', sequence_value=1, purchase_sequence_id=:s WHERE id=:p"),
            {"s": sequence, "p": purchase},
        )
        if received:
            receive(connection, purchase)
    return purchase


def receive(connection, purchase) -> None:
    connection.execute(
        text("UPDATE purchases SET inventory_operation_id=:i, received_at=now(), received_by_user_id=:u WHERE id=:p"),
        {"i": uuid4(), "u": uuid4(), "p": purchase},
    )


def test_confirmed_purchase_admits_one_complete_receipt(engine) -> None:
    """Spec 020 (RC-MVP-1): la recepción se registra una sola vez y completa (entrada, fecha y usuario)."""
    purchase = setup_confirmed(engine, received=False)
    fails(engine, "UPDATE purchases SET observations='x' WHERE id=:p", {"p": purchase}, "solo admite su recepci")
    fails(engine, "UPDATE purchases SET inventory_operation_id=:i WHERE id=:p", {"p": purchase, "i": uuid4()}, "ck_purchases_receipt")
    fails(
        engine,
        "UPDATE purchases SET inventory_operation_id=:i, received_at=now(), received_by_user_id=:u, payment_method_name_snapshot='x' "
        "WHERE id=:p",
        {"p": purchase, "i": uuid4(), "u": uuid4()},
        "solo admite su recepci",
    )
    with engine.begin() as connection:
        receive(connection, purchase)
    fails(engine, "UPDATE purchases SET inventory_operation_id=:i WHERE id=:p", {"p": purchase, "i": uuid4()}, "una sola vez")
    fails(engine, "UPDATE purchases SET received_at=now() - interval '1 day' WHERE id=:p", {"p": purchase}, "una sola vez")


def test_confirmed_purchase_only_admits_receipt_or_cancellation(engine) -> None:
    purchase = setup_confirmed(engine)
    fails(engine, "UPDATE purchases SET observations='x' WHERE id=:p", {"p": purchase}, "solo admite su recepci")
    fails(
        engine,
        "UPDATE purchases SET status='CANCELLED', observations='x', cancelled_by_user_id=:u, cancelled_at=now(), "
        "cancellation_reason='x' WHERE id=:p",
        {"p": purchase, "u": uuid4()},
        "solo admite su recepci",
    )
    fails(
        engine,
        "UPDATE purchases SET status='CANCELLED', inventory_operation_id=NULL, received_at=NULL, received_by_user_id=NULL, "
        "cancelled_by_user_id=:u, cancelled_at=now(), cancellation_reason='x' WHERE id=:p",
        {"p": purchase, "u": uuid4()},
        "una sola vez",  # anular no borra la recepción
    )
    fails(engine, "UPDATE purchases SET number='CP-2' WHERE id=:p", {"p": purchase})
    fails(engine, "UPDATE purchases SET status='DRAFT', number=NULL WHERE id=:p", {"p": purchase}, "no admite cambios")
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE purchases SET status='CANCELLED', cancelled_by_user_id=:u, cancelled_at=now(), "
                "cancellation_reason='x', version=version+1 WHERE id=:p"
            ),
            {"u": uuid4(), "p": purchase},
        )
    fails(engine, "UPDATE purchases SET cancellation_reason='y' WHERE id=:p", {"p": purchase}, "no admite cambios")


def test_confirmed_pending_receipt_can_be_cancelled(engine) -> None:
    purchase = setup_confirmed(engine, received=False)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE purchases SET status='CANCELLED', cancelled_by_user_id=:u, cancelled_at=now(), "
                "cancellation_reason='x' WHERE id=:p"
            ),
            {"u": uuid4(), "p": purchase},
        )


def test_purchases_are_never_deleted(engine) -> None:
    with engine.begin() as connection:
        purchase = insert_purchase(connection)
    fails(engine, "DELETE FROM purchases WHERE id=:p", {"p": purchase}, "no admite")
    fails(engine, "TRUNCATE purchases CASCADE", {}, "no admite")


def test_details_change_only_in_draft(engine) -> None:
    with engine.begin() as connection:
        draft = insert_purchase(connection)
        detail = insert_detail(connection, draft)
        connection.execute(text("UPDATE purchase_details SET product_name_snapshot='x' WHERE id=:d"), {"d": detail})
        connection.execute(text("DELETE FROM purchase_details WHERE id=:d"), {"d": detail})
    purchase = setup_confirmed(engine)
    fails(engine, "UPDATE purchase_details SET quantity=5 WHERE purchase_id=:p", {"p": purchase}, "DRAFT")
    fails(engine, "DELETE FROM purchase_details WHERE purchase_id=:p", {"p": purchase}, "DRAFT")
    with pytest.raises(DBAPIError), engine.begin() as connection:
        insert_detail(connection, purchase, line_number=2)


def test_detail_cannot_move_to_another_purchase(engine) -> None:
    with engine.begin() as connection:
        first, second = insert_purchase(connection), insert_purchase(connection)
        detail = insert_detail(connection, first)
    fails(engine, "UPDATE purchase_details SET purchase_id=:p WHERE id=:d", {"p": second, "d": detail}, "no puede cambiar")


def test_counters_only_grow(engine) -> None:
    with engine.begin() as connection:
        sequence = insert_sequence(connection)
        connection.execute(
            text("INSERT INTO purchase_sequence_counters (purchase_sequence_id, period_key, current_number, created_by, updated_by) VALUES (:s, '', 5, 'x', 'x')"),
            {"s": sequence},
        )
        connection.execute(text("UPDATE purchase_sequence_counters SET current_number=6 WHERE purchase_sequence_id=:s"), {"s": sequence})
    fails(engine, "UPDATE purchase_sequence_counters SET current_number=3 WHERE purchase_sequence_id=:s", {"s": sequence}, "solo puede crecer")
    fails(engine, "UPDATE purchase_sequence_counters SET current_number=6 WHERE purchase_sequence_id=:s", {"s": sequence}, "solo puede crecer")
    fails(engine, "DELETE FROM purchase_sequence_counters WHERE purchase_sequence_id=:s", {"s": sequence}, "no admite")
    fails(engine, "DELETE FROM purchase_sequences WHERE id=:s", {"s": sequence}, "no admite")


def test_terminal_operations_never_change(engine) -> None:
    with engine.begin() as connection:
        company = uuid4()
        purchase = insert_purchase(connection, company_id=company)
        operation = insert_operation(connection, purchase, company)
        connection.execute(text("UPDATE purchase_operations SET error_code='COMPENSATION_PENDING', inventory_operation_id=:i WHERE id=:o"), {"o": operation, "i": uuid4()})
    fails(engine, "UPDATE purchase_operations SET inventory_operation_id=:i WHERE id=:o", {"o": operation, "i": uuid4()}, "no se reemplaza")
    fails(engine, "UPDATE purchase_operations SET idempotency_key='otra' WHERE id=:o", {"o": operation}, "no cambia")
    # D-02/D-07: el usuario operativo que inició la operación y el motivo son inmutables.
    fails(engine, "UPDATE purchase_operations SET application_user_id=:u WHERE id=:o", {"o": operation, "u": uuid4()}, "no cambia")
    fails(engine, "UPDATE purchase_operations SET reason='otro' WHERE id=:o", {"o": operation}, "no cambia")
    with engine.begin() as connection:
        connection.execute(text("UPDATE purchase_operations SET status='FAILED', completed_at=now() WHERE id=:o"), {"o": operation})
    fails(engine, "UPDATE purchase_operations SET status='SUCCEEDED' WHERE id=:o", {"o": operation}, "ya terminó")
    fails(engine, "DELETE FROM purchase_operations WHERE id=:o", {"o": operation}, "no admite")


def test_lifecycle_events_are_immutable(engine) -> None:
    with engine.begin() as connection:
        purchase = insert_purchase(connection)
        event = uuid4()
        connection.execute(
            text(
                "INSERT INTO purchase_lifecycle_events (id, company_id, purchase_id, event_type, occurred_at, "
                "recorded_by_user_id, source, created_by) VALUES (:id, :c, :p, 'ORDERED', now(), :u, 'USER', 'x')"
            ),
            {"id": event, "c": uuid4(), "p": purchase, "u": uuid4()},
        )
    fails(engine, "UPDATE purchase_lifecycle_events SET notes='x' WHERE id=:e", {"e": event}, "no admite")
    fails(engine, "DELETE FROM purchase_lifecycle_events WHERE id=:e", {"e": event}, "no admite")
    fails(engine, "TRUNCATE purchase_lifecycle_events", {}, "no admite")
