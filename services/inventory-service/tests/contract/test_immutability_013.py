"""Inmutabilidad de ajustes, consumos, capas y conteos finalizados (R-12, RC-12, SC-005; T009)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from tests.contract.db_rows import (
    insert_adjustment,
    insert_consumption,
    insert_count,
    insert_count_detail,
    insert_layer,
    insert_movement,
    insert_operation,
)

NOW = datetime(2026, 10, 6, tzinfo=UTC)


@pytest.fixture
def rows(test_engine, clean_database):
    with test_engine.begin() as connection:
        operation = insert_operation(connection, operation_type="ADJUSTMENT", origin_type="ADJUSTMENT")
        movement = insert_movement(
            connection,
            operation,
            movement_type="NEGATIVE_ADJUSTMENT",
            origin_type="ADJUSTMENT",
            previous_balance=10,
            new_balance=7,
            quantity=3,
        )
        adjustment = insert_adjustment(connection, operation, movement)
        layer = insert_layer(connection)
        consumption = insert_consumption(connection, movement, layer)
    return {"adjustment": adjustment, "layer": layer, "consumption": consumption}


def _count(test_engine, rows: dict) -> int:
    with test_engine.connect() as connection:
        return sum(
            connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
            for table in ("inventory_adjustments", "inventory_cost_consumptions", "inventory_cost_layers")
        )


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE inventory_adjustments SET reason = 'x'",
        "DELETE FROM inventory_adjustments",
        "TRUNCATE inventory_adjustments CASCADE",
        "UPDATE inventory_cost_consumptions SET quantity = 1",
        "DELETE FROM inventory_cost_consumptions",
        "TRUNCATE inventory_cost_consumptions CASCADE",
        "DELETE FROM inventory_cost_layers",
        "TRUNCATE inventory_cost_layers CASCADE",
    ],
)
def test_forbidden_changes_are_rejected_and_rows_stay(test_engine, rows, statement) -> None:
    with test_engine.connect() as connection:
        with pytest.raises(DBAPIError) as error:
            with connection.begin():
                connection.execute(text(statement))
    assert "inmutable" in str(error.value) or "no se elimina" in str(error.value) or "no permitido" in str(error.value)
    assert _count(test_engine, rows) == 3


def test_layers_remaining_quantity_can_be_updated(test_engine, rows) -> None:
    with test_engine.begin() as connection:
        connection.execute(
            text("UPDATE inventory_cost_layers SET remaining_quantity = 4 WHERE id = :id"), {"id": rows["layer"]}
        )
        assert connection.execute(text("SELECT remaining_quantity FROM inventory_cost_layers")).scalar_one() == 4


def _finalized_count(connection, status: str):
    if status == "CANCELLED":
        return insert_count(
            connection, status="CANCELLED", cancelled_by_user_id=uuid4(), cancelled_at=NOW, cancel_reason="Motivo"
        )
    operation = insert_operation(connection, operation_type="ADJUSTMENT", origin_type="COUNT")
    return insert_count(
        connection,
        status="COMPLETED",
        started_at=NOW,
        completed_by_user_id=uuid4(),
        completed_at=NOW,
        operation_id=operation,
    )


@pytest.mark.parametrize("status", ["COMPLETED", "CANCELLED"])
@pytest.mark.parametrize(
    "statement",
    ["UPDATE inventory_count_details SET counted_quantity = 1, difference_quantity = -9", "DELETE FROM inventory_count_details"],
)
def test_details_of_finalized_counts_are_immutable(test_engine, clean_database, status, statement) -> None:
    with test_engine.begin() as connection:
        count = _finalized_count(connection, status)
        insert_count_detail(connection, count)

    with test_engine.connect() as connection:
        with pytest.raises(DBAPIError) as error:
            with connection.begin():
                connection.execute(text(statement))
    assert "finalizado" in str(error.value)

    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM inventory_count_details")).scalar_one() == 1


def test_details_of_counts_in_progress_can_change(test_engine, clean_database) -> None:
    with test_engine.begin() as connection:
        count = insert_count(connection, status="IN_PROGRESS", started_at=NOW)
        insert_count_detail(connection, count)
        connection.execute(text("UPDATE inventory_count_details SET counted_quantity = 9, difference_quantity = -1"))
        connection.execute(text("DELETE FROM inventory_count_details"))
        assert connection.execute(text("SELECT count(*) FROM inventory_count_details")).scalar_one() == 0
