"""Búsqueda progresiva por lotes (T092; FR-022-134, FR-022-135, FR-022-136; CP-96 a CP-98, CP-104)."""

from __future__ import annotations

import asyncio

import pytest

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.progressive_search import progressive_search
from tests.unit.search_support import ListConductor, SetEvaluator, rows


def run(conductor, evaluators, **kwargs):
    options = dict(need=21, batch_size=40, max_batches=5, work_time_seconds=5)
    options.update(kwargs)
    return asyncio.run(progressive_search(conductor, evaluators, **options))


def test_another_batch_only_when_valid_ones_are_missing() -> None:
    data = rows(200)
    conductor = ListConductor(data)
    outcome = run(conductor, [SetEvaluator({row[1] for row in data})])
    assert len(conductor.calls) == 1 and len(outcome.valid) == 40

    sparse = ListConductor(data)
    evaluator = SetEvaluator({row[1] for row in data[::4]})
    outcome = run(sparse, [evaluator])
    assert len(sparse.calls) == 3  # 10 + 10 + 10 válidos → se detiene al tener 21 o más
    assert len(outcome.valid) >= 21


def test_stops_when_need_is_reached_without_more_batches() -> None:
    data = rows(500)
    conductor = ListConductor(data)
    outcome = run(conductor, [SetEvaluator({row[1] for row in data[:21]})])
    assert len(conductor.calls) == 1 and [c.key for c in outcome.valid] == [row[1] for row in data[:21]]
    assert not outcome.exhausted and not outcome.limited


def test_evaluators_run_in_parallel_on_the_batch_ids_only_and_intersect() -> None:
    data = rows(40)
    first = SetEvaluator({row[1] for row in data[:30]})
    second = SetEvaluator({row[1] for row in data[10:]})
    outcome = run(ListConductor(data), [first, second], need=100)
    assert first.batches == second.batches == [[row[1] for row in data]]
    assert [c.key for c in outcome.valid] == [row[1] for row in data[10:30]]


def test_unknown_ids_are_not_valid() -> None:
    data = rows(10)
    outcome = run(ListConductor(data), [SetEvaluator({"id-que-no-existe"})], need=5)
    assert outcome.valid == [] and outcome.exhausted


def test_evaluator_failure_is_503_and_never_discards_candidates() -> None:
    async def failing(candidates):
        raise DependencyUnavailableError("product-catalog", "products_match_candidates", "tiempo_agotado")

    with pytest.raises(DependencyUnavailableError):
        run(ListConductor(rows(50)), [failing])


def test_conductor_order_is_preserved() -> None:
    data = rows(60, ties=3)
    outcome = run(ListConductor(data), [SetEvaluator({row[1] for row in data[::2]})], need=100)
    assert [c.key for c in outcome.valid] == [row[1] for row in sorted(data)][::2]


def test_work_limit_by_batches_and_by_time_checked_between_batches() -> None:
    data = rows(1000)
    conductor = ListConductor(data)
    outcome = run(conductor, [SetEvaluator(set())], max_batches=3)
    assert outcome.limited and len(conductor.calls) == 3 and outcome.examined == 120

    clock = {"now": 0.0}
    timed = ListConductor(data)

    async def slow_evaluator(candidates):
        clock["now"] += 2.0  # cada lote "tarda" 2 s
        return set()

    outcome = asyncio.run(progressive_search(timed, [slow_evaluator], need=21, batch_size=40, max_batches=50,
                                             work_time_seconds=5, started_at=0.0, clock=lambda: clock["now"]))
    assert outcome.limited and len(timed.calls) == 3  # 2 s, 4 s y 6 s: el tercero empezó antes de 5 s y se terminó


def test_empty_conductor_is_exhausted() -> None:
    outcome = run(ListConductor([]), [])
    assert outcome.valid == [] and outcome.exhausted and outcome.last_examined is None
