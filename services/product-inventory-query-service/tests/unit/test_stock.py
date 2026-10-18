"""Existencias, equivalencias y estado frente al mínimo (T099; FR-022-41, FR-022-42, FR-022-50, CP-31 a CP-42)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from product_inventory_query_service.application.ports import Balance, Policy
from product_inventory_query_service.domain.stock import (
    branch_stock,
    equivalence,
    fmt,
    minimum_state,
    shortfall,
    stock_state,
    total_quantity,
)

PRODUCT, A, B = uuid4(), uuid4(), uuid4()


def balance(branch, quantity, registered=True):
    return Balance(PRODUCT, branch, Decimal(quantity), registered)


def test_sum_by_product_and_balance_state() -> None:
    branches = [branch_stock(A, balance(A, "120"), None, with_minimums=False),
                branch_stock(B, None, None, with_minimums=False)]
    assert total_quantity(branches) == Decimal("120")
    assert [b.balance_state for b in branches] == ["REGISTERED", "NOT_REGISTERED"]
    zero = branch_stock(A, balance(A, "0"), None, with_minimums=False)
    unregistered = branch_stock(A, balance(A, "0", registered=False), None, with_minimums=False)
    assert (zero.balance_state, unregistered.balance_state) == ("REGISTERED", "NOT_REGISTERED")
    assert zero.base_quantity == unregistered.base_quantity == Decimal("0")


def test_equivalences_never_multiply_stock_by_presentation() -> None:
    """120 tabletas con caja x 10 → 12 cajas y resto 0, nunca 120 cajas."""
    box = equivalence(uuid4(), Decimal("120"), Decimal("10"))
    assert (box.whole_units, box.remainder_base_quantity) == (12, Decimal("0"))
    pack = equivalence(uuid4(), Decimal("125.5"), Decimal("12"))
    assert (pack.whole_units, fmt(pack.remainder_base_quantity)) == (10, "5.5000")
    unit = equivalence(uuid4(), Decimal("7"), Decimal("1"))
    assert unit.whole_units == 7
    with pytest.raises(ValueError):
        equivalence(uuid4(), Decimal("1"), Decimal("0"))


def test_four_decimals() -> None:
    assert fmt(Decimal("3")) == "3.0000"
    assert fmt(Decimal("2.5")) == "2.5000"


@pytest.mark.parametrize(
    ("quantity", "minimum", "state"),
    [("3", None, "NO_POLICY"), ("3", "5", "BELOW_MINIMUM"), ("5", "5", "AT_MINIMUM"), ("9", "5", "ABOVE_MINIMUM"),
     ("0", "0", "AT_MINIMUM"), ("0", None, "NO_POLICY")],
)
def test_minimum_states(quantity, minimum, state) -> None:
    assert minimum_state(Decimal(quantity), Decimal(minimum) if minimum is not None else None) == state


def test_minimum_zero_never_alerts_and_shortfall() -> None:
    assert minimum_state(Decimal("0"), Decimal("0")) != "BELOW_MINIMUM"
    assert shortfall(Decimal("3"), Decimal("5")) == Decimal("2")


def test_branch_stock_with_minimums_only_when_visible() -> None:
    policy = Policy(PRODUCT, A, Decimal("5"))
    with_minimums = branch_stock(A, balance(A, "3"), policy, with_minimums=True)
    assert (with_minimums.minimum_stock, with_minimums.minimum_state) == (Decimal("5"), "BELOW_MINIMUM")
    without = branch_stock(A, balance(A, "3"), policy, with_minimums=False)
    assert without.minimum_stock is None and without.minimum_state is None
    no_policy = branch_stock(A, None, None, with_minimums=True)
    assert (no_policy.minimum_stock, no_policy.minimum_state) == (None, "NO_POLICY")


def test_stock_state() -> None:
    assert stock_state(Decimal("0.0001")) == "IN_STOCK"
    assert stock_state(Decimal("0")) == "OUT_OF_STOCK"
