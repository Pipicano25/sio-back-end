"""Cursor `PAGE` (T090; FR-022-63, FR-022-64, CP-72, CP-73, CP-132 a CP-134).

El cursor apunta al **último producto entregado**: los válidos sobrantes de un lote se vuelven a encontrar en la
página siguiente; nada se repite ni se omite.
"""

from __future__ import annotations

import asyncio

from product_inventory_query_service.application.progressive_search import progressive_search
from product_inventory_query_service.domain.pagination import derive_page
from tests.unit.search_support import ListConductor, SetEvaluator, rows


def page(conductor, evaluators, *, page_size, after=None, max_batches=5):
    outcome = asyncio.run(progressive_search(conductor, evaluators, need=page_size + 1,
                                             batch_size=min(max(page_size * 2, 20), 40), max_batches=max_batches,
                                             work_time_seconds=5, after=after))
    return derive_page(outcome, page_size)


def walk(conductor, evaluators, page_size) -> list[list[str]]:
    pages, after = [], None
    for _ in range(1000):
        result = page(conductor, evaluators, page_size=page_size, after=after)
        assert len(result.items) <= page_size
        pages.append([item.key for item in result.items])
        if not result.has_next:
            return pages
        assert result.cursor_kind == "PAGE"
        after = result.cursor_position
    raise AssertionError("no terminó")


def test_first_page_has_page_size_items_and_page_cursor_at_last_delivered() -> None:
    data = rows(100)
    result = page(ListConductor(data), [], page_size=20)
    assert [item.key for item in result.items] == [row[1] for row in data[:20]]
    assert result.has_next and result.cursor_kind == "PAGE" and not result.partial
    assert result.cursor_position == {"k": [data[19][0]], "id": data[19][1]}


def test_25_valid_in_a_batch_of_40_the_next_page_delivers_the_remaining_5() -> None:
    data = rows(40)
    valid = {row[1] for row in data[:25]}
    first = page(ListConductor(data), [SetEvaluator(valid)], page_size=20)
    assert len(first.items) == 20 and first.has_next
    second = page(ListConductor(data), [SetEvaluator(valid)], page_size=20, after=first.cursor_position)
    assert [item.key for item in second.items] == [row[1] for row in data[20:25]]
    assert not second.has_next and second.cursor_kind is None


def test_ties_at_the_page_border_are_resolved_by_id() -> None:
    data = rows(30, ties=3)  # nombres repetidos de a tres
    pages = walk(ListConductor(data), [], 4)
    flat = [key for block in pages for key in block]
    assert flat == [row[1] for row in sorted(data)]
    assert len(flat) == len(set(flat))


def test_exact_last_page_has_no_next() -> None:
    data = rows(20)
    result = page(ListConductor(data), [], page_size=20)
    assert len(result.items) == 20 and result.has_next is False and result.cursor_position is None


def test_full_walk_with_filter_has_no_gaps_or_duplicates() -> None:
    data = rows(500, ties=2)
    valid = {row[1] for index, row in enumerate(data) if index % 7 in (0, 3)}
    for page_size in (1, 5, 13, 20):
        flat = [key for block in walk(ListConductor(data), [SetEvaluator(valid)], page_size) for key in block]
        assert flat == [row[1] for row in sorted(data) if row[1] in valid]
