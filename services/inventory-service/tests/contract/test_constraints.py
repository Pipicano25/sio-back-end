"""Cada `CHECK` y `UNIQUE` de `data-model.md` rechaza una inserción directa inválida (T010)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from tests.contract.db_rows import insert_balance, insert_movement, insert_operation


@pytest.fixture
def conn(test_engine, clean_database):
    with test_engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


def _rejects(conn, constraint: str | tuple[str, ...], action) -> None:
    """La inserción falla por la restricción indicada (o por alguna de ellas, si la fila viola varias)."""
    savepoint = conn.begin_nested()
    with pytest.raises(IntegrityError) as error:
        action()
    savepoint.rollback()
    names = (constraint,) if isinstance(constraint, str) else constraint
    assert any(f'"{name}"' in str(error.value) for name in names), str(error.value)[:200]


def test_valid_rows_are_accepted(conn) -> None:
    operation = insert_operation(conn)
    insert_balance(conn, quantity=10, version=1)
    insert_movement(conn, operation, unit_cost=1500)


# inventory_operations ----------------------------------------------------------


def test_operation_key_is_unique(conn) -> None:
    key = uuid4()
    insert_operation(conn, operation_key=key)
    _rejects(conn, "uq_inventory_operations_operation_key", lambda: insert_operation(conn, operation_key=key))


def test_operation_type_and_origin_type(conn) -> None:
    _rejects(conn, ("ck_inventory_operations_type", "ck_inventory_operations_origin_type"), lambda: insert_operation(conn, operation_type="ADJUSTMENT"))
    _rejects(conn, "ck_inventory_operations_origin_type", lambda: insert_operation(conn, operation_type="OUTPUT", origin_type="PURCHASE"))
    _rejects(conn, "ck_inventory_operations_origin_type", lambda: insert_operation(conn, origin_type="SALE"))


def test_reversal_link_and_reason(conn) -> None:
    original = insert_operation(conn)
    _rejects(conn, "ck_inventory_operations_reversal_link", lambda: insert_operation(conn, operation_type="ENTRY_REVERSAL", reason="x"))
    _rejects(conn, "ck_inventory_operations_reversal_link", lambda: insert_operation(conn, reverses_operation_id=original))
    _rejects(conn, "ck_inventory_operations_reason", lambda: insert_operation(conn, operation_type="ENTRY_REVERSAL", reverses_operation_id=original))
    _rejects(conn, "ck_inventory_operations_reason", lambda: insert_operation(conn, reason="  "))
    _rejects(conn, "ck_inventory_operations_reason", lambda: insert_operation(conn, reason="x" * 2001))
    insert_operation(conn, operation_type="ENTRY_REVERSAL", reverses_operation_id=original, reason="Anulación")
    _rejects(
        conn,
        "uq_inventory_operations_reverses",
        lambda: insert_operation(conn, operation_type="ENTRY_REVERSAL", reverses_operation_id=original, reason="Otra"),
    )


def test_line_count_and_request_hash(conn) -> None:
    _rejects(conn, "ck_inventory_operations_line_count", lambda: insert_operation(conn, line_count=0))
    _rejects(conn, "ck_inventory_operations_line_count", lambda: insert_operation(conn, line_count=101))
    _rejects(conn, "ck_inventory_operations_request_hash_format", lambda: insert_operation(conn, request_hash="A" * 64))
    _rejects(conn, "ck_inventory_operations_request_hash_format", lambda: insert_operation(conn, request_hash="abc"))


# inventory_balances ------------------------------------------------------------


def test_balance_rules(conn) -> None:
    _rejects(conn, "ck_inventory_balances_quantity_non_negative", lambda: insert_balance(conn, quantity=-1))
    _rejects(conn, "ck_inventory_balances_version_non_negative", lambda: insert_balance(conn, version=-1))
    company, branch, product = uuid4(), uuid4(), uuid4()
    insert_balance(conn, company_id=company, branch_id=branch, company_product_id=product)
    _rejects(
        conn,
        "uq_inventory_balances_product",
        lambda: insert_balance(conn, company_id=company, branch_id=branch, company_product_id=product),
    )


# inventory_movements -----------------------------------------------------------


def test_movement_quantities_and_math(conn) -> None:
    op = insert_operation(conn)
    _rejects(conn, "ck_inventory_movements_quantity_positive", lambda: insert_movement(conn, op, quantity=0, new_balance=0))
    _rejects(conn, "ck_inventory_movements_balances_non_negative", lambda: insert_movement(conn, op, movement_type="SALE_OUTPUT", origin_type="SALE", quantity=5, previous_balance=2, new_balance=-3))
    _rejects(conn, "ck_inventory_movements_balance_math", lambda: insert_movement(conn, op, new_balance=9))
    _rejects(conn, "ck_inventory_movements_balance_math", lambda: insert_movement(conn, op, movement_type="SALE_OUTPUT", origin_type="SALE", previous_balance=20, new_balance=30))
    _rejects(conn, ("ck_inventory_movements_type", "ck_inventory_movements_balance_math"), lambda: insert_movement(conn, op, movement_type="POSITIVE_ADJUSTMENT"))


def test_unit_cost_only_on_entries(conn) -> None:
    op = insert_operation(conn)
    _rejects(conn, "ck_inventory_movements_unit_cost", lambda: insert_movement(conn, op, movement_type="SALE_OUTPUT", origin_type="SALE", previous_balance=10, new_balance=0, unit_cost=5))
    _rejects(conn, "ck_inventory_movements_unit_cost", lambda: insert_movement(conn, op, unit_cost=-1))


def test_reversal_link_and_uniqueness(conn) -> None:
    op = insert_operation(conn)
    original = insert_movement(conn, op)
    _rejects(conn, "ck_inventory_movements_reversal_link", lambda: insert_movement(conn, op, line_index=1, reversed_movement_id=original))
    _rejects(conn, "ck_inventory_movements_reversal_link", lambda: insert_movement(conn, op, line_index=1, movement_type="ENTRY_REVERSAL", previous_balance=10, new_balance=0))
    insert_movement(conn, op, line_index=1, movement_type="ENTRY_REVERSAL", previous_balance=10, new_balance=0, reversed_movement_id=original)
    _rejects(
        conn,
        "uq_inventory_movements_reversed",
        lambda: insert_movement(conn, op, line_index=2, movement_type="ENTRY_REVERSAL", previous_balance=10, new_balance=0, reversed_movement_id=original),
    )


def test_sequence_and_line_uniqueness(conn) -> None:
    op = insert_operation(conn)
    company, branch, product = uuid4(), uuid4(), uuid4()
    insert_movement(conn, op, company_id=company, branch_id=branch, company_product_id=product, balance_sequence=1)
    _rejects(
        conn,
        "uq_inventory_movements_sequence",
        lambda: insert_movement(conn, op, line_index=1, company_id=company, branch_id=branch, company_product_id=product, balance_sequence=1),
    )
    _rejects(conn, "uq_inventory_movements_operation_line", lambda: insert_movement(conn, op, line_index=0))


def test_audit_columns_unchanged(conn) -> None:
    op = insert_operation(conn)
    _rejects(conn, "ck_inventory_movements_audit_unchanged", lambda: insert_movement(conn, op, updated_by="otro"))
