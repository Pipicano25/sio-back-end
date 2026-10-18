"""Adaptador de Inventory (T065; FR-022-15, RC-022-2): los costos nunca llegan al dominio."""

from __future__ import annotations

import asyncio
import dataclasses
import json
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.ports import Balance
from product_inventory_query_service.infrastructure.inventory import HTTPInventory
from tests.contract.adapter_support import Recorder, technical

COST_FIELDS = {"inventory_value", "average_unit_cost", "has_unknown_cost", "unit_cost"}


def _inv(responder) -> tuple[HTTPInventory, Recorder]:
    recorder = Recorder(responder)
    return HTTPInventory(technical("inventory", recorder)), recorder


def test_balances_drop_costs_and_mark_unregistered() -> None:
    company, branch, registered, unregistered = (uuid4() for _ in range(4))
    pc, _ = _inv(lambda r: httpx.Response(200, json={"items": [
        {"company_id": str(company), "branch_id": str(branch), "company_product_id": str(registered),
         "quantity": "120.0000", "balance_sequence": 4, "last_movement_at": "2026-10-01T00:00:00Z",
         "inventory_value": "540000.00", "average_unit_cost": "4500.0000", "has_unknown_cost": False},
        {"company_id": str(company), "branch_id": str(branch), "company_product_id": str(unregistered),
         "quantity": "0.0000", "balance_sequence": 0, "last_movement_at": None,
         "inventory_value": "0.00", "average_unit_cost": None, "has_unknown_cost": False},
    ]}))
    balances = asyncio.run(pc.balances(company, branch, [registered, unregistered]))
    assert balances[registered] == Balance(registered, branch, Decimal("120.0000"), True)
    assert balances[unregistered].registered is False
    assert not ({field.name for field in dataclasses.fields(Balance)} & COST_FIELDS)
    assert "540000" not in repr(balances) and "4500" not in repr(balances)


def test_balances_of_another_company_or_branch_are_discarded() -> None:
    company, branch = uuid4(), uuid4()
    pc, _ = _inv(lambda r: httpx.Response(200, json={"items": [
        {"company_id": str(uuid4()), "branch_id": str(branch), "company_product_id": str(uuid4()),
         "quantity": "1", "balance_sequence": 1}]}))
    assert asyncio.run(pc.balances(company, branch, [uuid4()])) == {}


def test_policies_product_sets_pairs_and_summary() -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()

    def responder(request):
        path = request.url.path
        body = json.loads(request.content)
        if path.endswith("/inventory-policies/lookup"):
            return httpx.Response(200, json={"items": [
                {"company_product_id": str(product), "policy": {"id": str(uuid4()), "minimum_stock": "5.0000", "status": "ACTIVE"}},
                {"company_product_id": str(uuid4()), "policy": None}]})
        if path.endswith("/inventory-product-sets") and body.get("unit") == "PAIRS":
            return httpx.Response(200, json={"items": [{
                "company_product_id": str(product), "branch_id": str(branch), "base_quantity": "3.0000",
                "minimum_stock": "5.0000", "shortfall": "2.0000",
                "position": {"k": ["2.0000"], "id": str(product), "branch_id": str(branch)}}], "has_more": False})
        if path.endswith("/inventory-product-sets"):
            return httpx.Response(200, json={"items": [{"company_product_id": str(product), "position": {"k": [], "id": str(product)}}],
                                             "has_more": True})
        counts = {"products_with_positive_balance": 1, "products_with_zero_balance": 0, "products_with_policy": 1,
                  "products_below_minimum": 1, "inventory_value": "10.00"}  # se ignora si llegara
        return httpx.Response(200, json={"branches": [{"branch_id": str(branch), **counts}], "consolidated": counts})

    inv, recorder = _inv(responder)
    policies = asyncio.run(inv.policies(company, branch, [product]))
    assert list(policies) == [product] and policies[product].minimum_stock == Decimal("5.0000")
    page, has_more = asyncio.run(inv.product_set(company, [branch], stock_state="IN_STOCK", minimum_state=None, limit=40))
    assert page[0][0] == product and has_more
    pairs, _ = asyncio.run(inv.below_minimum_pairs(company, [branch], limit=20))
    assert pairs[0].shortfall == Decimal("2.0000")
    summary = asyncio.run(inv.summary(company, [branch]))
    assert summary.consolidated.products_below_minimum == 1
    assert not hasattr(summary.consolidated, "inventory_value")
    assert recorder.bodies()[-1] == {"branch_ids": [str(branch)]}  # sin `include_valuation`
    assert recorder.bodies()[1] == {"branch_ids": [str(branch)], "limit": 40, "stock_state": "IN_STOCK"}
    assert recorder.bodies()[2]["unit"] == "PAIRS"


def test_pairs_of_branches_not_requested_are_discarded_and_errors_503() -> None:
    company, branch = uuid4(), uuid4()
    inv, _ = _inv(lambda r: httpx.Response(200, json={"items": [{
        "company_product_id": str(uuid4()), "branch_id": str(uuid4()), "base_quantity": "0", "minimum_stock": "1",
        "shortfall": "1", "position": {"k": ["1"], "id": "x"}}], "has_more": False}))
    pairs, _ = asyncio.run(inv.below_minimum_pairs(company, [branch], limit=5))
    assert pairs == []
    inv, _ = _inv(lambda r: httpx.Response(503, json={}))
    with pytest.raises(DependencyUnavailableError):
        asyncio.run(inv.balances(company, branch, [uuid4()]))
