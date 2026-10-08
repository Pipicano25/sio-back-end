"""Visibilidad de la rentabilidad (FR-027a, DS-12, C-08; research.md R-02; T011)."""

from __future__ import annotations

import pytest

from sales_service.api.profitability import (
    HEADER_FIELDS,
    LINE_FIELDS,
    can_read_profitability,
    strip_profitability,
)


@pytest.mark.parametrize(
    "roles",
    [
        {"perm:sales:sales:read-profitability"},
        {"perm:all:all:all"},
        {"perm:sales:all:all"},  # comodín de acción: por eso el grupo ventas ya no lo tiene (C-08)
        {"perm:sales:sales:all"},
    ],
)
def test_roles_that_grant_profitability(roles) -> None:
    assert can_read_profitability(roles)


@pytest.mark.parametrize(
    "roles",
    [
        set(),
        {"perm:sales:all:read"},
        {"perm:sales:sales:read"},
        {"perm:all:all:read"},  # supervisores: la acción read no cubre read-profitability
        {"perm:sales:all:create", "perm:sales:all:read", "perm:sales:all:update", "perm:sales:all:delete"},
        {"perm:sales:sale_details:read-profitability"},
        {"ventas", "supervisor"},
    ],
)
def test_roles_that_do_not_grant_profitability(roles) -> None:
    assert not can_read_profitability(roles)


def _sale() -> dict:
    line = {
        "id": "l1",
        "unit_price": "16000.0000",
        "unit_cost_snapshot": "1200.5000",
        "cost_total": "14406.00",
        "cost_known": True,
        "gross_margin_amount": "1594.00",
        "gross_margin_percentage": "9.9625",
        "subtotal": "16000.00",
    }
    return {"id": "s1", "total": "16000.00", "has_unknown_cost": False, "lines": [line, dict(line, id="l2")]}


def test_fields_are_removed_not_nulled() -> None:
    body = strip_profitability(_sale())
    assert "has_unknown_cost" not in body
    for line in body["lines"]:
        for name in LINE_FIELDS:
            assert name not in line
        assert line["unit_price"] == "16000.0000" and line["subtotal"] == "16000.00"
    assert body["total"] == "16000.00"


def test_works_for_lists_and_lines_without_header() -> None:
    page = {"items": [{"id": "s1", "has_unknown_cost": True}], "page": 1}
    assert strip_profitability(page) == {"items": [{"id": "s1"}], "page": 1}
    lines = {"items": [_sale()["lines"][0]]}
    assert set(strip_profitability(lines)["items"][0]) == {"id", "unit_price", "subtotal"}


def test_field_sets_match_the_contract() -> None:
    assert LINE_FIELDS == (
        "unit_cost_snapshot",
        "cost_total",
        "cost_known",
        "gross_margin_amount",
        "gross_margin_percentage",
    )
    assert HEADER_FIELDS == ("has_unknown_cost",)
