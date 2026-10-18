"""Tamaño de los lotes internos y objetivo de búsqueda (T084; FR-022-62, FR-022-133, CP-75)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from product_inventory_query_service.domain.planner import BatchPolicy, plan
from product_inventory_query_service.domain.query_spec import Endpoint, QuerySpec
from tests.conftest import build_test_settings


@pytest.mark.parametrize(("page_size", "batch"), [(1, 20), (5, 20), (10, 20), (15, 30), (20, 40)])
def test_batch_formula_and_need(page_size: int, batch: int) -> None:
    result = plan(QuerySpec(Endpoint.PRODUCT_OVERVIEWS, uuid4(), page_size=page_size), BatchPolicy())
    assert result.batch_size == batch
    assert result.need == page_size + 1


def test_configured_values_are_used() -> None:
    settings = build_test_settings(batch_min=10, batch_factor=3, batch_max=50)
    policy = BatchPolicy(settings.batch_min, settings.batch_factor, settings.batch_max, settings.max_batches_per_request,
                         settings.work_time_seconds)
    assert plan(QuerySpec(Endpoint.PRODUCT_OVERVIEWS, uuid4(), page_size=2), policy).batch_size == 10
    assert plan(QuerySpec(Endpoint.PRODUCT_OVERVIEWS, uuid4(), page_size=15), policy).batch_size == 45
    assert plan(QuerySpec(Endpoint.PRODUCT_OVERVIEWS, uuid4(), page_size=20), policy).batch_size == 50
    assert settings.batch_size(15) == 45
