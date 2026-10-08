"""Asignación concurrente con hilos reales contra PostgreSQL (RC-02; T045)."""

from __future__ import annotations

import threading

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from sales_service.infrastructure.models import SaleSequence
from sales_service.infrastructure.sequence_repository import SequenceRepository
from tests.contract.db_rows import insert_sequence


def run_concurrently(base_engine, sequence_id, period: str, workers: int) -> list[int]:
    engine = create_engine(base_engine.url, pool_size=workers + 2, max_overflow=0)
    barrier = threading.Barrier(workers)
    results: list[int] = []
    errors: list[BaseException] = []
    lock = threading.Lock()

    def work() -> None:
        try:
            with Session(engine) as session:
                sequence = session.get(SaleSequence, sequence_id)
                barrier.wait(10)
                value = SequenceRepository(session).assign(sequence, period, "sub-hilo")
                session.commit()
            with lock:
                results.append(value)
        except BaseException as error:  # noqa: BLE001
            with lock:
                errors.append(error)

    threads = [threading.Thread(target=work) for _ in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    engine.dispose()
    assert not errors, errors
    return results


def test_fifty_concurrent_assignments_are_unique_and_consecutive(test_engine, clean_database) -> None:
    with test_engine.begin() as connection:
        sequence = insert_sequence(connection, reset_policy="MONTHLY")
    results = run_concurrently(test_engine, sequence, "202610", 50)
    assert sorted(results) == list(range(1, 51))


def test_concurrent_first_numbers_of_a_new_period(test_engine, clean_database) -> None:
    with test_engine.begin() as connection:
        sequence = insert_sequence(connection, reset_policy="YEARLY")
    results = run_concurrently(test_engine, sequence, "2027", 2)
    assert sorted(results) == [1, 2]
