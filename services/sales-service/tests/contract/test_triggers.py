"""Triggers de ciclo de vida e inmutabilidad (data-model.md; RC-03, RN-04; T014)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.contract.db_rows import insert_detail, insert_operation, insert_sale, insert_sequence


@pytest.fixture
def engine(test_engine, clean_database):
    return test_engine


def fails(engine, sql: str, params: dict, fragment: str = "") -> None:
    with pytest.raises(DBAPIError) as error, engine.begin() as connection:
        connection.execute(text(sql), params)
    assert fragment in str(error.value)


def setup_confirmed(engine):
    with engine.begin() as connection:
        sequence = insert_sequence(connection)
        sale = insert_sale(connection)
        insert_detail(connection, sale)
        connection.execute(
            text(
                "UPDATE sales SET status='CONFIRMED', number='FV-1', sequence_value=1, "
                "sale_sequence_id=:s, inventory_operation_id=:i WHERE id=:p"
            ),
            {"s": sequence, "i": uuid4(), "p": sale},
        )
    return sale


def test_confirmed_sale_only_admits_cancellation(engine) -> None:
    sale = setup_confirmed(engine)
    fails(engine, "UPDATE sales SET observations='x' WHERE id=:p", {"p": sale}, "no admite cambios")
    fails(
        engine,
        "UPDATE sales SET status='CANCELLED', observations='x', cancelled_by_user_id=:u, cancelled_at=now(), "
        "cancellation_reason='x' WHERE id=:p",
        {"p": sale, "u": uuid4()},
        "solo admite su anulaci",
    )
    fails(engine, "UPDATE sales SET number='FV-2' WHERE id=:p", {"p": sale})
    fails(engine, "UPDATE sales SET inventory_operation_id=:i WHERE id=:p", {"p": sale, "i": uuid4()})
    fails(engine, "UPDATE sales SET status='DRAFT', number=NULL WHERE id=:p", {"p": sale})
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE sales SET status='CANCELLED', cancelled_by_user_id=:u, cancelled_at=now(), "
                "cancellation_reason='x', version=version+1 WHERE id=:p"
            ),
            {"u": uuid4(), "p": sale},
        )
    fails(engine, "UPDATE sales SET cancellation_reason='y' WHERE id=:p", {"p": sale}, "no admite cambios")


def test_sales_are_never_deleted(engine) -> None:
    with engine.begin() as connection:
        sale = insert_sale(connection)
    fails(engine, "DELETE FROM sales WHERE id=:p", {"p": sale}, "no admite")
    fails(engine, "TRUNCATE sales CASCADE", {}, "no admite")


def test_details_change_only_in_draft(engine) -> None:
    with engine.begin() as connection:
        draft = insert_sale(connection)
        detail = insert_detail(connection, draft)
        connection.execute(text("UPDATE sale_details SET product_name_snapshot='x' WHERE id=:d"), {"d": detail})
        connection.execute(text("DELETE FROM sale_details WHERE id=:d"), {"d": detail})
    sale = setup_confirmed(engine)
    fails(engine, "UPDATE sale_details SET quantity=5 WHERE sale_id=:p", {"p": sale}, "DRAFT")
    fails(engine, "DELETE FROM sale_details WHERE sale_id=:p", {"p": sale}, "DRAFT")
    with pytest.raises(DBAPIError), engine.begin() as connection:
        insert_detail(connection, sale, line_number=2)


def test_detail_cannot_move_to_another_sale(engine) -> None:
    with engine.begin() as connection:
        first, second = insert_sale(connection), insert_sale(connection)
        detail = insert_detail(connection, first)
    fails(engine, "UPDATE sale_details SET sale_id=:p WHERE id=:d", {"p": second, "d": detail}, "no puede cambiar")


def test_counters_only_grow(engine) -> None:
    with engine.begin() as connection:
        sequence = insert_sequence(connection)
        connection.execute(
            text("INSERT INTO sale_sequence_counters (sale_sequence_id, period_key, current_number, created_by, updated_by) VALUES (:s, '', 5, 'x', 'x')"),
            {"s": sequence},
        )
        connection.execute(text("UPDATE sale_sequence_counters SET current_number=6 WHERE sale_sequence_id=:s"), {"s": sequence})
    fails(engine, "UPDATE sale_sequence_counters SET current_number=3 WHERE sale_sequence_id=:s", {"s": sequence}, "solo puede crecer")
    fails(engine, "UPDATE sale_sequence_counters SET current_number=6 WHERE sale_sequence_id=:s", {"s": sequence}, "solo puede crecer")
    fails(engine, "DELETE FROM sale_sequence_counters WHERE sale_sequence_id=:s", {"s": sequence}, "no admite")
    fails(engine, "DELETE FROM sale_sequences WHERE id=:s", {"s": sequence}, "no admite")


def test_terminal_operations_never_change(engine) -> None:
    with engine.begin() as connection:
        company = uuid4()
        sale = insert_sale(connection, company_id=company)
        operation = insert_operation(connection, sale, company)
        connection.execute(text("UPDATE sale_operations SET error_code='COMPENSATION_PENDING', inventory_operation_id=:i WHERE id=:o"), {"o": operation, "i": uuid4()})
    fails(engine, "UPDATE sale_operations SET inventory_operation_id=:i WHERE id=:o", {"o": operation, "i": uuid4()}, "no se reemplaza")
    fails(engine, "UPDATE sale_operations SET idempotency_key='otra' WHERE id=:o", {"o": operation}, "no cambia")
    # D-02/D-07: el usuario operativo que inició la operación y el motivo son inmutables.
    fails(engine, "UPDATE sale_operations SET application_user_id=:u WHERE id=:o", {"o": operation, "u": uuid4()}, "no cambia")
    fails(engine, "UPDATE sale_operations SET reason='otro' WHERE id=:o", {"o": operation}, "no cambia")
    with engine.begin() as connection:
        connection.execute(text("UPDATE sale_operations SET status='FAILED', completed_at=now() WHERE id=:o"), {"o": operation})
    fails(engine, "UPDATE sale_operations SET status='SUCCEEDED' WHERE id=:o", {"o": operation}, "ya terminó")
    fails(engine, "DELETE FROM sale_operations WHERE id=:o", {"o": operation}, "no admite")


def test_cost_and_margin_are_frozen_after_confirmation(engine) -> None:
    """RN-04: costo, margen y precio se escriben antes de confirmar y no cambian después."""
    with engine.begin() as connection:
        sequence = insert_sequence(connection)
        sale = insert_sale(connection)
        detail = insert_detail(connection, sale)
        # En la transacción que confirma: primero las líneas (venta aún DRAFT), luego la cabecera.
        connection.execute(
            text(
                "UPDATE sale_details SET unit_cost_snapshot=4, cost_total=4, cost_known=true, "
                "gross_margin_amount=6, gross_margin_percentage=60 WHERE id=:d"
            ),
            {"d": detail},
        )
        connection.execute(
            text(
                "UPDATE sales SET status='CONFIRMED', number='FV-9', sequence_value=9, sale_sequence_id=:s, "
                "inventory_operation_id=:i, has_unknown_cost=false WHERE id=:p"
            ),
            {"s": sequence, "i": uuid4(), "p": sale},
        )
    fails(engine, "UPDATE sale_details SET cost_total=1 WHERE id=:d", {"d": detail}, "DRAFT")
    fails(engine, "UPDATE sale_details SET gross_margin_percentage=NULL WHERE id=:d", {"d": detail}, "DRAFT")
    fails(engine, "UPDATE sale_details SET unit_price=99 WHERE id=:d", {"d": detail}, "DRAFT")
    fails(engine, "UPDATE sales SET has_unknown_cost=true WHERE id=:p", {"p": sale}, "no admite cambios")
    fails(engine, "UPDATE sales SET operation_date='2026-10-07', due_date='2026-10-07' WHERE id=:p", {"p": sale})
