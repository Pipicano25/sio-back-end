"""Inmutabilidad en la base (R-06, RC-02, SC-005; T011)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.contract.db_rows import insert_balance, insert_movement, insert_operation


@pytest.fixture
def rows(test_engine, clean_database):
    with test_engine.begin() as connection:
        operation = insert_operation(connection)
        movement = insert_movement(connection, operation)
        balance = insert_balance(connection, quantity=10, version=1)
    return {"operation": operation, "movement": movement, "balance": balance}


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE inventory_movements SET reason = 'x'",
        "DELETE FROM inventory_movements",
        "TRUNCATE inventory_movements CASCADE",
        "UPDATE inventory_operations SET reason = 'x'",
        "DELETE FROM inventory_operations",
        "TRUNCATE inventory_operations CASCADE",
        "DELETE FROM inventory_balances",
        "TRUNCATE inventory_balances",
    ],
)
def test_forbidden_changes_are_rejected_and_rows_stay(test_engine, rows, statement) -> None:
    with test_engine.connect() as connection:
        with pytest.raises(DBAPIError) as error:
            with connection.begin():
                connection.execute(text(statement))
    assert "inmutable" in str(error.value) or "no se elimina" in str(error.value)

    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM inventory_movements")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM inventory_operations")).scalar_one() == 1
        assert connection.execute(text("SELECT count(*) FROM inventory_balances")).scalar_one() == 1


def test_balances_can_be_updated(test_engine, rows) -> None:
    with test_engine.begin() as connection:
        connection.execute(text("UPDATE inventory_balances SET quantity = 5, version = 2"))
        assert connection.execute(text("SELECT quantity FROM inventory_balances")).scalar_one() == 5
