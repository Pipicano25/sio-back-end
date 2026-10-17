"""Cálculo puro del precio automático (spec 021: FR-021-21, FR-021-23; T010).

Casos: CP-01, CP-02, CP-03, CP-04, CP-11, CP-12, CP-28, CP-57 (con una moneda de 0 decimales), CP-66 y CP-T13.
Todos los importes son ficticios; el 19 % de los ejemplos no es una tarifa real.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from commercial_relationship_service.domain.automatic_pricing import (
    Outcome,
    PriceEvaluation,
    decide,
    final_price,
    real_unit_cost,
    reference_cost,
)

D = Decimal


def test_cp01_first_receipt_with_tax_paid() -> None:
    """10 bolsas a 2.000 con 3.800 de impuesto: total 23.800, costo real 2.380 y precio con 30 % = 3.094."""
    current = real_unit_cost(D("23800.00"), D("10"))
    assert current == D("2380")
    assert reference_cost(current, None) == D("2380")
    assert final_price(D("2380"), D("30"), "COP") == D("3094")


def test_cp66_discount_and_tax_without_double_tax() -> None:
    """(subtotal − descuento + impuesto) / cantidad: 20.000 − 2.000 + 3.420 = 21.420 → 2.142; no se suma impuesto otra vez."""
    assert real_unit_cost(D("21420.00"), D("10")) == D("2142")
    assert final_price(D("2142"), D("0"), "COP") == D("2142")


def test_cp02_cost_increase_uses_current() -> None:
    assert reference_cost(D("3000"), D("2800")) == D("3000")
    assert reference_cost(D("2800"), D("2800")) == D("2800")  # igual → actual


def test_cp03_cost_decrease_uses_simple_average() -> None:
    assert reference_cost(D("2600"), D("2800")) == D("2700")


def test_cp04_each_receipt_compares_with_the_previous_real_cost() -> None:
    costs = [D("2800"), D("2600"), D("2400"), D("2700")]
    references = [reference_cost(cost, costs[index - 1] if index else None) for index, cost in enumerate(costs)]
    assert references == [D("2800"), D("2700"), D("2500"), D("2700")]  # la tercera usa 2.600, no 2.700


@pytest.mark.parametrize(
    ("markup", "expected"),
    [("0", "2000"), ("20", "2400"), ("50", "3000"), ("100", "4000"), ("150", "5000"), ("1000", "22000")],
)
def test_cp11_cp12_markup_examples(markup: str, expected: str) -> None:
    assert final_price(D("2000"), D(markup), "COP") == D(expected)


def test_cp57_round_half_up_once_in_a_zero_decimal_currency() -> None:
    assert final_price(D("2700.5"), D("0"), "CLP") == D("2701")
    assert final_price(D("2700.49"), D("0"), "CLP") == D("2700")


def test_cp57_cop_keeps_two_decimals_from_the_currency_table() -> None:
    """Decisión del 2026-10-15: COP conserva 2 decimales (Spec 007, ISO 4217)."""
    assert final_price(D("2700.505"), D("0"), "COP") == D("2700.51")
    assert str(final_price(D("2380"), D("30"), "COP")) == "3094.00"


def test_two_decimal_currency_rounds_to_cents() -> None:
    assert final_price(D("10.005"), D("0"), "USD") == D("10.01")
    assert final_price(D("2380"), D("30"), "USD") == D("3094.00")


def test_cpt13_non_terminating_division_is_rounded_only_at_the_end() -> None:
    """10.000 / 3 = 3.333,33… y con 15 % 3.833,33… → 3.833 en CLP: el cociente no se redondea antes del precio."""
    current = real_unit_cost(D("10000.00"), D("3"))
    assert current == D("10000") / D("3")
    assert final_price(current, D("15"), "CLP") == D("3833")
    # Promedio con medio: (2.801 + 2.600) / 2 = 2.700,5 → sin redondeo intermedio → 2.701 en CLP.
    average = reference_cost(D("2600"), D("2801"))
    assert average == D("2700.5")
    assert final_price(average, D("0"), "CLP") == D("2701")


@pytest.mark.parametrize("quantity", ["0", "-1"])
def test_real_unit_cost_requires_positive_quantity(quantity: str) -> None:
    with pytest.raises(ValueError):
        real_unit_cost(D("100"), D(quantity))


def _evaluation(**overrides) -> PriceEvaluation:
    values = dict(
        list_effective=True,
        currency_matches=True,
        presentation_active=True,
        current_unit_cost=D("2380"),
        has_policy=True,
        current_price=D("3000"),
        has_future_prices=False,
        new_price=D("3094"),
    )
    values.update(overrides)
    return PriceEvaluation(**values)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"list_effective": False}, Outcome.SKIPPED_LIST_NOT_EFFECTIVE),
        ({"currency_matches": False}, Outcome.SKIPPED_CURRENCY_MISMATCH),
        ({"presentation_active": False}, Outcome.SKIPPED_PRESENTATION_INACTIVE),
        ({"current_unit_cost": D("0")}, Outcome.SKIPPED_ZERO_COST),  # CP-28
        # RC-021-13 (2026-10-16): sin política nunca se toca el precio, haya o no vigente o futuros
        ({"has_policy": False}, Outcome.SKIPPED_NO_POLICY),
        ({"has_policy": False, "current_price": None}, Outcome.SKIPPED_NO_POLICY),
        ({"has_policy": False, "current_price": None, "has_future_prices": True}, Outcome.SKIPPED_NO_POLICY),
        ({"has_policy": False, "has_future_prices": True}, Outcome.SKIPPED_NO_POLICY),
        ({"new_price": D("3000")}, Outcome.UNCHANGED),  # CP-21
        ({}, Outcome.APPLIED),
        ({"current_price": None}, Outcome.APPLIED),  # CP-01: primer precio
    ],
)
def test_decide_follows_fr_021_23_order(overrides: dict, expected: Outcome) -> None:
    assert decide(_evaluation(**overrides)) is expected


def test_decide_checks_list_before_cost() -> None:
    """El orden de FR-021-23 es estable: una lista vencida se omite aunque el costo también sea 0."""
    assert decide(_evaluation(list_effective=False, current_unit_cost=D("0"))) is Outcome.SKIPPED_LIST_NOT_EFFECTIVE
