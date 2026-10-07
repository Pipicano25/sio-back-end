"""Repositorio: operación, bloqueos y `balance_sequence` sin huecos (R-03, R-04; T028)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from inventory_service.application.exceptions import InsufficientStockError
from inventory_service.infrastructure.repository import (
    KeyTakenError,
    NewLine,
    NewOperation,
    SqlInventoryRepository,
)


def new_operation(company, branch, lines, *, operation_type="ENTRY", key=None) -> NewOperation:
    return NewOperation(
        operation_key=key or uuid4(),
        client_id="inventory-test-operator",
        created_by="sub-sa-inventory-test-operator",
        operation_type=operation_type,
        company_id=company,
        branch_id=branch,
        origin_type="PURCHASE" if operation_type == "ENTRY" else "SALE",
        origin_id=uuid4(),
        application_user_id=uuid4(),
        correlation_id=uuid4(),
        reason=None,
        reverses_operation_id=None,
        request_hash="b" * 64,
        # 013 (DS-12): toda entrada lleva costo y la empresa su moneda.
        currency_code="COP",
        lines=[
            NewLine(
                index=i,
                origin_detail_id=uuid4(),
                company_product_id=p,
                quantity=Decimal(q),
                unit_cost=Decimal("10") if operation_type == "ENTRY" else None,
            )
            for i, (p, q) in enumerate(lines)
        ],
    )


@pytest.fixture
def repo_factory(test_engine, clean_database):
    sessions = []

    def make() -> SqlInventoryRepository:
        session = Session(test_engine, expire_on_commit=False)
        sessions.append(session)
        return SqlInventoryRepository(session, lock_timeout_ms=5000)

    yield make
    for session in sessions:
        session.close()


def kardex(test_engine, product):
    with test_engine.connect() as connection:
        return connection.execute(
            text(
                "SELECT balance_sequence, previous_balance, new_balance FROM inventory_movements "
                "WHERE company_product_id = :p ORDER BY balance_sequence"
            ),
            {"p": product},
        ).all()


def test_apply_creates_balance_and_assigns_sequence_after_lock(repo_factory, test_engine) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    stored = repo_factory().apply_operation(new_operation(company, branch, [(product, "10"), (product, "2")]))
    assert [m.balance_sequence for m in stored.movements] == [1, 2]
    assert [(m.previous_balance, m.new_balance) for m in stored.movements] == [(0, 10), (10, 12)]
    with test_engine.connect() as connection:
        row = connection.execute(text("SELECT quantity, version FROM inventory_balances")).one()
    assert (row.quantity, row.version) == (Decimal("12"), 2)


def test_rollback_leaves_no_gap_in_the_sequence(repo_factory, test_engine) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    repo_factory().apply_operation(new_operation(company, branch, [(product, "5")]))
    with pytest.raises(InsufficientStockError):
        repo_factory().apply_operation(new_operation(company, branch, [(product, "1"), (product, "9")], operation_type="OUTPUT"))
    repo_factory().apply_operation(new_operation(company, branch, [(product, "1")], operation_type="OUTPUT"))
    assert [row.balance_sequence for row in kardex(test_engine, product)] == [1, 2]
    rows = kardex(test_engine, product)
    assert rows[1].previous_balance == rows[0].new_balance


def test_key_taken_inserts_nothing(repo_factory, test_engine) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    key = uuid4()
    repo_factory().apply_operation(new_operation(company, branch, [(product, "1")], key=key))
    with pytest.raises(KeyTakenError):
        repo_factory().apply_operation(new_operation(company, branch, [(product, "1")], key=key))
    assert len(kardex(test_engine, product)) == 1


def test_find_by_key_rebuilds_the_result(repo_factory) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    operation = new_operation(company, branch, [(product, "4")])
    stored = repo_factory().apply_operation(operation)
    found = repo_factory().find_by_key(operation.operation_key)
    assert found.id == stored.id
    assert found.request_hash == "b" * 64
    assert [m.id for m in found.movements] == [m.id for m in stored.movements]
    assert found.balances_after == {product: Decimal("4")}
