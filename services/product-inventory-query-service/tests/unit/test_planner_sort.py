"""Orden efectivo y `sort_applied` (T083; FR-022-60, FR-022-65, CP-140, CP-141, CP-154)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from product_inventory_query_service.api.filters.query_params import parse_query
from product_inventory_query_service.application.exceptions import ValidationFailedError
from product_inventory_query_service.domain.planner import BatchPolicy, plan
from product_inventory_query_service.domain.query_spec import Endpoint
from product_inventory_query_service.domain.routes import Conductor, Route

COMPANY = uuid4()


def applied(endpoint=Endpoint.PRODUCT_OVERVIEWS, *pairs) -> tuple[Route, str]:
    result = plan(parse_query(endpoint, COMPANY, list(pairs)), BatchPolicy())
    return result.route, result.sort_applied


def test_default_order_per_route() -> None:
    assert applied() == (Route.R_E, "display_name:asc")
    assert applied(Endpoint.PRODUCT_OVERVIEWS, ("search", "x")) == (Route.R_B, "display_name:asc")
    assert applied(Endpoint.PRODUCT_OVERVIEWS, ("internal_code", "C1")) == (Route.R_A2, "display_name:asc")
    assert applied(Endpoint.PRODUCT_OVERVIEWS, ("brand_id", str(uuid4()))) == (Route.R_C, "canonical_name:asc")
    assert applied(Endpoint.PRODUCT_OVERVIEWS, ("barcode", "7702")) == (Route.R_A1, "canonical_name:asc")
    assert applied(Endpoint.INVENTORY_OVERVIEWS, ("stock_state", "IN_STOCK")) == (Route.R_D, "company_product_id:asc")
    assert applied(Endpoint.LOW_STOCK_PRODUCTS) == (Route.R_D, "shortfall:desc")


def test_explicit_sort_on_cr_field_makes_cr_conduct() -> None:
    assert applied(Endpoint.PRODUCT_OVERVIEWS, ("brand_id", str(uuid4())), ("sort", "display_name")) == (Route.R_F, "display_name:asc")
    assert applied(Endpoint.LOW_STOCK_PRODUCTS, ("sort", "created_at:desc")) == (Route.R_F, "created_at:desc")
    result = plan(parse_query(Endpoint.INVENTORY_OVERVIEWS, COMPANY, [("stock_state", "IN_STOCK"), ("sort", "internal_code")]),
                  BatchPolicy())
    assert result.conductor is Conductor.CR


@pytest.mark.parametrize("pairs", [[], [("search", "x")], [("internal_code", "C1")]])
def test_omitting_or_sending_the_default_is_equivalent_on_cr_routes(pairs) -> None:
    implicit = plan(parse_query(Endpoint.PRODUCT_OVERVIEWS, COMPANY, pairs), BatchPolicy())
    explicit = plan(parse_query(Endpoint.PRODUCT_OVERVIEWS, COMPANY, [*pairs, ("sort", "display_name:asc")]), BatchPolicy())
    assert (implicit.route, implicit.sort_applied, implicit.evaluators) == (explicit.route, explicit.sort_applied, explicit.evaluators)


def test_invalid_sort_is_422() -> None:
    with pytest.raises(ValidationFailedError):
        parse_query(Endpoint.PRODUCT_OVERVIEWS, COMPANY, [("sort", "shortfall")])
