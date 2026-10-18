"""Rutas del planificador (T081; FR-022-131, FR-022-132, CP-90 a CP-95)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from product_inventory_query_service.domain.planner import BatchPolicy, Evaluator, plan
from product_inventory_query_service.domain.query_spec import Endpoint, QuerySpec, Sort
from product_inventory_query_service.domain.routes import Conductor, Route

COMPANY = uuid4()
BRAND = uuid4()


def spec(endpoint=Endpoint.PRODUCT_OVERVIEWS, **kwargs) -> QuerySpec:
    return QuerySpec(endpoint=endpoint, company_id=COMPANY, **kwargs)


def route_of(**kwargs):
    result = plan(spec(**kwargs), BatchPolicy())
    return result.route, result.conductor, result.evaluators


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({}, (Route.R_E, Conductor.CR, ())),
        ({"search": "colgate"}, (Route.R_B, Conductor.CR, ())),
        ({"internal_code": "000045"}, (Route.R_A2, Conductor.CR, ())),
        ({"sku": "ACE-CJ100"}, (Route.R_A2, Conductor.CR, ())),
        ({"barcode": "7702010000017"}, (Route.R_A1, Conductor.PC, (Evaluator.CR,))),
        ({"identifier": "IUM-1"}, (Route.R_A1, Conductor.PC, (Evaluator.CR,))),
        ({"brand_ids": (BRAND,)}, (Route.R_C, Conductor.PC, (Evaluator.CR,))),
        ({"has_image": False}, (Route.R_C, Conductor.PC, (Evaluator.CR,))),
        ({"stock_state": "IN_STOCK"}, (Route.R_D, Conductor.INVENTORY, (Evaluator.CR,))),
        ({"stock_state": "OUT_OF_STOCK"}, (Route.R_E, Conductor.CR, (Evaluator.INVENTORY_STOCK,))),
    ],
)
def test_each_route_with_conductor_and_evaluators(kwargs, expected) -> None:
    assert route_of(**kwargs) == expected


def test_search_with_has_image_starts_with_cr_and_evaluates_pc() -> None:
    """CP-91: `search=Colgate&has_image=true` → R-B: CR conduce, PC evalúa, sin sondeos."""
    assert route_of(search="Colgate", has_image=True) == (Route.R_B, Conductor.CR, (Evaluator.PC,))


def test_barcode_wins_over_internal_code_and_search() -> None:
    assert route_of(barcode="7702", internal_code="C1", search="x")[0] is Route.R_A1


def test_out_of_stock_and_no_policy_never_drive() -> None:
    assert route_of(stock_state="OUT_OF_STOCK")[1] is Conductor.CR
    result = plan(spec(Endpoint.INVENTORY_OVERVIEWS, minimum_state="NO_POLICY"), BatchPolicy())
    assert result.conductor is Conductor.CR and result.evaluators == (Evaluator.INVENTORY_MINIMUM,)
    combined = plan(spec(Endpoint.INVENTORY_OVERVIEWS, brand_ids=(BRAND,), stock_state="OUT_OF_STOCK"), BatchPolicy())
    assert combined.conductor is Conductor.PC
    assert combined.evaluators == (Evaluator.CR, Evaluator.INVENTORY_STOCK)


def test_inventory_drives_minimum_states_and_combined_stock() -> None:
    result = plan(spec(Endpoint.INVENTORY_OVERVIEWS, minimum_state="BELOW_MINIMUM", stock_state="IN_STOCK"), BatchPolicy())
    assert result.route is Route.R_D and result.evaluators == (Evaluator.CR,)
    with_out_of_stock = plan(spec(Endpoint.INVENTORY_OVERVIEWS, minimum_state="AT_MINIMUM", stock_state="OUT_OF_STOCK"),
                             BatchPolicy())
    assert with_out_of_stock.conductor is Conductor.INVENTORY
    assert with_out_of_stock.evaluators == (Evaluator.CR, Evaluator.INVENTORY_STOCK)


def test_low_stock_uses_r_d_with_pairs_unless_explicit_sort() -> None:
    low = plan(spec(Endpoint.LOW_STOCK_PRODUCTS), BatchPolicy())
    assert (low.route, low.conductor, low.evaluators, low.pairs) == (Route.R_D, Conductor.INVENTORY, (Evaluator.CR,), True)
    with_brand = plan(spec(Endpoint.LOW_STOCK_PRODUCTS, brand_ids=(BRAND,)), BatchPolicy())
    assert with_brand.evaluators == (Evaluator.CR, Evaluator.PC)
    sorted_low = plan(spec(Endpoint.LOW_STOCK_PRODUCTS, sort=Sort("display_name")), BatchPolicy())
    assert (sorted_low.route, sorted_low.conductor) == (Route.R_F, Conductor.CR)
    assert sorted_low.evaluators == (Evaluator.INVENTORY_MINIMUM,)


def test_cr_is_always_an_evaluator_when_it_does_not_drive() -> None:
    for kwargs in ({"brand_ids": (BRAND,)}, {"stock_state": "IN_STOCK"}, {"barcode": "1"}):
        result = plan(spec(Endpoint.INVENTORY_OVERVIEWS, **kwargs), BatchPolicy())
        assert result.conductor is not Conductor.CR and Evaluator.CR in result.evaluators


def test_explicit_sort_on_non_cr_routes_gives_r_f() -> None:
    result = plan(spec(brand_ids=(BRAND,), sort=Sort("display_name")), BatchPolicy())
    assert (result.route, result.conductor, result.evaluators) == (Route.R_F, Conductor.CR, (Evaluator.PC,))


def test_low_stock_is_always_r_d_even_with_search_or_catalog_filters() -> None:
    for kwargs in ({"search": "x"}, {"barcode": "7702"}, {"brand_ids": (BRAND,)}, {"internal_code": "C1"}):
        result = plan(spec(Endpoint.LOW_STOCK_PRODUCTS, **kwargs), BatchPolicy())
        assert (result.route, result.conductor) == (Route.R_D, Conductor.INVENTORY), kwargs
        assert Evaluator.CR in result.evaluators
