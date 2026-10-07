"""Propiedad RC-15 contra PostgreSQL: Σ capas = saldo y valor = Σ capas tras cada operación (SC-004; T024)."""

from __future__ import annotations

import random
from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from inventory_service.application.exceptions import (
    EntryLayerConsumedError,
    InsufficientStockError,
    ValidationFailedError,
)
from inventory_service.domain.rounding import money
from inventory_service.infrastructure.repository import NewLine, NewOperation, SqlInventoryRepository

SEQUENCES = 200
STEPS = 8


def operation(company, branch, kind, lines, *, reverses=None) -> NewOperation:
    origin = {"ENTRY": "PURCHASE", "OUTPUT": "SALE", "ENTRY_REVERSAL": "PURCHASE", "OUTPUT_REVERSAL": "SALE"}.get(
        kind, "ADJUSTMENT"
    )
    return NewOperation(
        operation_key=uuid4(),
        client_id="inventory-test-operator",
        created_by="sub-propiedad",
        operation_type=kind,
        company_id=company,
        branch_id=branch,
        origin_type=origin,
        origin_id=uuid4(),
        application_user_id=uuid4(),
        correlation_id=uuid4(),
        reason="Prueba de propiedad" if kind in ("ENTRY_REVERSAL", "OUTPUT_REVERSAL", "ADJUSTMENT") else None,
        reverses_operation_id=reverses,
        request_hash="d" * 64,
        currency_code="COP",
        lines=lines,
    )


def check_invariant(session: Session, company, branch, product) -> None:
    rows = session.execute(
        text(
            "SELECT b.company_product_id, b.quantity, b.inventory_value, b.has_unknown_cost, "
            "COALESCE(SUM(l.remaining_quantity) FILTER (WHERE l.status = 'OPEN'), 0) AS layers "
            "FROM inventory_balances b LEFT JOIN inventory_cost_layers l USING (company_id, branch_id, company_product_id) "
            "WHERE b.company_id = :c AND b.branch_id = :b AND b.company_product_id = :p GROUP BY 1, 2, 3, 4"
        ),
        {"c": company, "b": branch, "p": product},
    ).all()
    for row in rows:
        assert row.quantity == row.layers
        open_layers = session.execute(
            text(
                "SELECT remaining_quantity, unit_cost, cost_known FROM inventory_cost_layers "
                "WHERE company_id = :c AND branch_id = :b AND company_product_id = :p AND status = 'OPEN'"
            ),
            {"c": company, "b": branch, "p": row.company_product_id},
        ).all()
        assert row.inventory_value == money(sum((money(item.remaining_quantity * item.unit_cost) for item in open_layers), D(0)))
        assert row.has_unknown_cost == any(not item.cost_known for item in open_layers)
    session.rollback()


@pytest.fixture
def repo(test_engine, clean_database):
    session = Session(test_engine, expire_on_commit=False)
    yield SqlInventoryRepository(session, lock_timeout_ms=5000), session
    session.close()


def test_random_sequences_keep_layers_and_value_equal_to_the_balance(repo) -> None:
    repository, session = repo
    company, branch = uuid4(), uuid4()

    for seed in range(SEQUENCES):
        rng = random.Random(seed)
        product = uuid4()
        entries, outputs = [], []

        for _ in range(STEPS):
            action = rng.choice(["entry", "entry", "output", "output", "positive", "negative", "reverse_output", "reverse_entry"])
            quantity = D(rng.randint(1, 40)) / 4
            try:
                if action == "entry":
                    stored = repository.apply_operation(
                        operation(company, branch, "ENTRY", [NewLine(0, uuid4(), product, quantity, D(rng.randint(0, 99999)) / 100)])
                    )
                    entries.append(stored)
                elif action == "output":
                    outputs.append(repository.apply_operation(operation(company, branch, "OUTPUT", [NewLine(0, uuid4(), product, quantity, None)])))
                elif action in ("positive", "negative"):
                    movement = "POSITIVE_ADJUSTMENT" if action == "positive" else "NEGATIVE_ADJUSTMENT"
                    cost = D(rng.randint(1, 5000)) / 10 if rng.random() < 0.5 else None
                    repository.apply_operation(
                        operation(
                            company,
                            branch,
                            "ADJUSTMENT",
                            [NewLine(0, uuid4(), product, quantity, cost if action == "positive" else None, movement_type=movement)],
                        )
                    )
                elif action == "reverse_output" and outputs:
                    original = outputs.pop(rng.randrange(len(outputs)))
                    lines = [
                        NewLine(m.line_index, m.origin_detail_id, m.company_product_id, m.quantity, None, reversed_movement_id=m.id)
                        for m in original.movements
                    ]
                    repository.apply_operation(operation(company, branch, "OUTPUT_REVERSAL", lines, reverses=original.id))
                elif action == "reverse_entry" and entries:
                    original = entries.pop(rng.randrange(len(entries)))
                    lines = [
                        NewLine(m.line_index, m.origin_detail_id, m.company_product_id, m.quantity, None, reversed_movement_id=m.id)
                        for m in original.movements
                    ]
                    repository.apply_operation(operation(company, branch, "ENTRY_REVERSAL", lines, reverses=original.id))
            except (InsufficientStockError, EntryLayerConsumedError, ValidationFailedError):
                pass  # rechazos válidos: no cambian nada

            check_invariant(session, company, branch, product)
