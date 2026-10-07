"""Asignación atómica y contadores por período (R-03, FR-032, FR-033; T040)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from purchase_service.domain.numbering import format_number, period_key
from purchase_service.infrastructure.sequence_repository import SequenceRepository
from tests.contract.db_rows import insert_sequence


@pytest.fixture
def engine(test_engine, clean_database):
    return test_engine


def assign(engine, sequence_id, period: str, *, commit: bool = True) -> int:
    with Session(engine) as session:
        repository = SequenceRepository(session)
        sequence = repository.get(repository_company(session, sequence_id), sequence_id)
        value = repository.assign(sequence, period, "sub-prueba")
        if commit:
            session.commit()
        else:
            session.rollback()
        return value


def repository_company(session, sequence_id):
    from purchase_service.infrastructure.models import PurchaseSequence

    return session.get(PurchaseSequence, sequence_id).company_id


def test_independent_counter_per_period(engine) -> None:
    with engine.begin() as connection:
        sequence = insert_sequence(connection, reset_policy="MONTHLY")
    assert assign(engine, sequence, "202610") == 1
    assert assign(engine, sequence, "202610") == 2
    assert assign(engine, sequence, "202611") == 1
    assert assign(engine, sequence, "202610") == 3  # compra retroactiva de octubre confirmada en noviembre
    numbers = [format_number("CP", "-", "202610", 3, 6), format_number("CP", "-", "202611", 1, 6)]
    assert numbers == ["CP-202610-000003", "CP-202611-000001"]


def test_first_number_is_initial_number(engine) -> None:
    with engine.begin() as connection:
        sequence = insert_sequence(connection, initial_number=500)
    assert assign(engine, sequence, "") == 500
    assert assign(engine, sequence, "") == 501


def test_rollback_does_not_consume_numbers(engine) -> None:
    with engine.begin() as connection:
        sequence = insert_sequence(connection)
    assert assign(engine, sequence, "") == 1
    assert assign(engine, sequence, "", commit=False) == 2
    assert assign(engine, sequence, "") == 2


def test_applicable_prefers_branch_over_company(engine) -> None:
    company, branch, other_branch = uuid4(), uuid4(), uuid4()
    with engine.begin() as connection:
        company_sequence = insert_sequence(connection, company_id=company, series_code="EMP")
        branch_sequence = insert_sequence(connection, company_id=company, branch_id=branch, series_code="SUC")
        insert_sequence(connection, company_id=company, branch_id=other_branch, series_code="OTRA", is_active=False)
    with Session(engine) as session:
        repository = SequenceRepository(session)
        assert repository.applicable(company, branch).id == branch_sequence
        assert repository.applicable(company, other_branch).id == company_sequence
        assert repository.applicable(uuid4(), branch) is None


def test_period_key_by_policy() -> None:
    from datetime import date

    assert [period_key(policy, date(2026, 10, 6)) for policy in ("NEVER", "YEARLY", "MONTHLY")] == ["", "2026", "202610"]
