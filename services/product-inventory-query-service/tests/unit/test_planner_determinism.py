"""Plan determinista y sin E/S (T082; FR-022-130, FR-022-142, CP-105)."""

from __future__ import annotations

import ast
import random
from pathlib import Path
from uuid import uuid4

from product_inventory_query_service.api.filters.query_params import parse_query
from product_inventory_query_service.domain import planner as planner_module
from product_inventory_query_service.domain import routes as routes_module
from product_inventory_query_service.domain.planner import BatchPolicy, plan
from product_inventory_query_service.domain.query_spec import Endpoint

COMPANY = uuid4()
PAIRS = [("search", "Colgate"), ("has_image", "true"), ("brand_id", str(uuid4())), ("brand_id", str(uuid4())),
         ("stock_state", "IN_STOCK"), ("page_size", "15"), ("sort", "internal_code:desc"), ("branch_id", str(uuid4()))]


def test_same_parameters_same_plan_in_any_order() -> None:
    expected = plan(parse_query(Endpoint.PRODUCT_OVERVIEWS, COMPANY, PAIRS), BatchPolicy())
    rng = random.Random(22)
    for _ in range(1000):
        shuffled = PAIRS[:]
        rng.shuffle(shuffled)
        assert plan(parse_query(Endpoint.PRODUCT_OVERVIEWS, COMPANY, shuffled), BatchPolicy()) == expected


def test_cursor_does_not_change_the_plan() -> None:
    base = plan(parse_query(Endpoint.PRODUCT_OVERVIEWS, COMPANY, PAIRS), BatchPolicy())
    with_cursor = plan(parse_query(Endpoint.PRODUCT_OVERVIEWS, COMPANY, [*PAIRS, ("cursor", "v1.abc.def")]), BatchPolicy())
    assert base == with_cursor


def _imports(module) -> set[str]:
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_planner_modules_do_not_import_io() -> None:
    for module in (planner_module, routes_module):
        imports = _imports(module)
        assert not any("infrastructure" in name or name.startswith(("httpx", "asyncio", "fastapi")) for name in imports), imports


def test_planning_makes_no_calls() -> None:
    """El plan se obtiene sin dependencias: no recibe puertos ni dobles."""
    import inspect

    assert list(inspect.signature(plan).parameters) == ["spec", "policy"]
