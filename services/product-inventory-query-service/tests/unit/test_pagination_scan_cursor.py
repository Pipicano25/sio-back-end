"""Cursor `SCAN` (T091; FR-022-136, CP-99, CP-100, CP-142, CP-143).

Al alcanzar el límite de trabajo se entregan **todos** los válidos encontrados y el cursor apunta al último
candidato examinado: como no queda ningún válido sin entregar antes de esa posición, no se pierde ni se repite nada.
"""

from __future__ import annotations

import asyncio

from product_inventory_query_service.application.progressive_search import progressive_search
from product_inventory_query_service.domain.pagination import WORK_LIMIT_REACHED, derive_page
from tests.unit.search_support import ListConductor, SetEvaluator, rows


def page(conductor, evaluators, *, page_size=20, after=None, max_batches=1):
    outcome = asyncio.run(progressive_search(conductor, evaluators, need=page_size + 1, batch_size=40,
                                             max_batches=max_batches, work_time_seconds=5, after=after))
    return derive_page(outcome, page_size)


def test_limit_reached_delivers_all_valid_with_scan_cursor_at_last_examined() -> None:
    data = rows(1000)
    valid = {row[1] for row in data[::150]}  # 7 válidos en 1.000
    result = page(ListConductor(data), [SetEvaluator(valid)], max_batches=5)
    assert [item.key for item in result.items] == [data[0][1], data[150][1]]
    assert result.has_next and result.partial and result.partial_reason == WORK_LIMIT_REACHED
    assert result.cursor_kind == "SCAN"
    assert result.cursor_position == {"k": [data[199][0]], "id": data[199][1]}


def test_partial_with_zero_items() -> None:
    data = rows(200)
    result = page(ListConductor(data), [SetEvaluator(set())], max_batches=1)
    assert result.items == [] and result.has_next and result.partial and result.cursor_kind == "SCAN"


def test_exhausted_in_the_same_batch_as_the_limit_is_not_partial() -> None:
    data = rows(30)
    result = page(ListConductor(data), [SetEvaluator({data[3][1]})], max_batches=1)
    assert [item.key for item in result.items] == [data[3][1]]
    assert result.has_next is False and result.partial is False and result.cursor_kind is None


def test_consecutive_scans_until_the_end_lose_and_repeat_nothing() -> None:
    data = rows(1000)
    valid = {row[1] for row in data[::150]}
    delivered, after, kinds = [], None, []
    for _ in range(100):
        result = page(ListConductor(data), [SetEvaluator(valid)], max_batches=1, after=after)
        delivered.extend(item.key for item in result.items)
        kinds.append(result.cursor_kind)
        if not result.has_next:
            break
        after = result.cursor_position
    assert delivered == [row[1] for row in data if row[1] in valid]
    assert "SCAN" in kinds and kinds[-1] is None


def test_scan_then_page_mix() -> None:
    """Un `SCAN` seguido de una página normal sigue sin omisiones ni duplicados."""
    data = rows(300)
    valid = {row[1] for row in data[250:]}  # todo lo válido está al final
    first = page(ListConductor(data), [SetEvaluator(valid)], max_batches=2)
    assert first.partial and first.items == []
    second = page(ListConductor(data), [SetEvaluator(valid)], max_batches=5, after=first.cursor_position)
    assert [item.key for item in second.items] == [row[1] for row in data[250:270]]
    assert second.cursor_kind == "PAGE"
