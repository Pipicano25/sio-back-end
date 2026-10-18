"""Análisis de los parámetros de los listados (T080; FR-022-61, FR-022-148, CP-76)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from product_inventory_query_service.api.filters.query_params import parse_query
from product_inventory_query_service.application.exceptions import ValidationFailedError
from product_inventory_query_service.domain.query_spec import Endpoint, Sort

P = Endpoint.PRODUCT_OVERVIEWS
COMPANY = uuid4()


def parse(*pairs, endpoint=P):
    return parse_query(endpoint, COMPANY, list(pairs))


def test_defaults() -> None:
    spec = parse()
    assert spec.page_size == 20
    assert spec.status == "ACTIVE"
    assert spec.branch_ids is None  # scope = COMPANY
    assert spec.sort is None and spec.cursor is None


@pytest.mark.parametrize("value", ["0", "21", "abc", "1.5", "-1"])
def test_page_size_out_of_range_or_not_integer_is_422(value) -> None:
    with pytest.raises(ValidationFailedError):
        parse(("page_size", value))


@pytest.mark.parametrize("value", ["1", "5", "20"])
def test_page_size_within_range(value) -> None:
    assert parse(("page_size", value)).page_size == int(value)


def test_unknown_or_repeated_scalar_parameter_is_422() -> None:
    with pytest.raises(ValidationFailedError) as exc:
        parse(("tenantId", "x"))
    assert exc.value.errors[0]["code"] == "UNKNOWN_FIELD"
    with pytest.raises(ValidationFailedError):
        parse(("search", "a"), ("search", "b"))


def test_search_length_and_blank() -> None:
    assert parse(("search", "   ")).search is None
    assert parse(("search", "x" * 200)).search == "x" * 200
    with pytest.raises(ValidationFailedError):
        parse(("search", "x" * 201))


def test_cursor_up_to_2048() -> None:
    assert parse(("cursor", "c" * 2048)).cursor == "c" * 2048
    with pytest.raises(ValidationFailedError):
        parse(("cursor", "c" * 2049))


def test_branch_scope_is_exclusive_and_repeatable_lists_are_deduplicated() -> None:
    branch, brand = uuid4(), uuid4()
    spec = parse(("branch_id", str(branch)), ("branch_id", str(branch)), ("brand_id", str(brand)), ("brand_id", str(brand)))
    assert spec.branch_ids == (branch,) and spec.brand_ids == (brand,)
    assert parse(("scope", "COMPANY")).branch_ids is None
    with pytest.raises(ValidationFailedError):
        parse(("scope", "COMPANY"), ("branch_id", str(branch)))
    with pytest.raises(ValidationFailedError):
        parse(("branch_id", "no-es-uuid"))


def test_endpoint_specific_filters() -> None:
    with pytest.raises(ValidationFailedError):
        parse(("stock_state", "IN_STOCK"), endpoint=Endpoint.LOW_STOCK_PRODUCTS)
    with pytest.raises(ValidationFailedError):
        parse(("minimum_state", "BELOW_MINIMUM"), endpoint=P)
    assert parse(("minimum_state", "NO_POLICY"), endpoint=Endpoint.INVENTORY_OVERVIEWS).minimum_state == "NO_POLICY"
    with pytest.raises(ValidationFailedError):
        parse(("price_list_id", str(uuid4())), endpoint=Endpoint.INVENTORY_OVERVIEWS)


def test_sort_values() -> None:
    assert parse(("sort", "internal_code:desc")).sort == Sort("internal_code", True)
    assert parse(("sort", "created_at")).sort == Sort("created_at", False)
    for invalid in ("price", "display_name:up", "canonical_name"):
        with pytest.raises(ValidationFailedError):
            parse(("sort", invalid))


def test_booleans_and_enums() -> None:
    assert parse(("has_image", "true")).has_image is True
    assert parse(("has_image", "0")).has_image is False
    with pytest.raises(ValidationFailedError):
        parse(("has_image", "quizas"))
    with pytest.raises(ValidationFailedError):
        parse(("status", "BLOQUEADO"))
