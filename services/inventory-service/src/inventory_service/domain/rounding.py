"""Redondeo de costos y valores de inventario (FR-055; research.md R-04).

- Costos unitarios con 4 decimales y valores monetarios con 2.
- `ROUND_HALF_UP` (convención contable: `0.005 → 0.01`), nunca el redondeo bancario.
- El valor de un saldo se **recalcula** desde sus capas abiertas, cada una redondeada
  por separado; no se acumula, así que no deriva con el tiempo.

Las operaciones usan un contexto decimal propio con precisión suficiente para
multiplicar dos `NUMERIC(18,4)` sin perder dígitos antes de redondear.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Context, Decimal

MONEY = Decimal("0.01")
UNIT = Decimal("0.0001")

_CONTEXT = Context(prec=60, rounding=ROUND_HALF_UP)


def money(value: Decimal) -> Decimal:
    """Valor monetario con 2 decimales (`ROUND_HALF_UP`)."""
    return value.quantize(MONEY, rounding=ROUND_HALF_UP, context=_CONTEXT)


def unit(value: Decimal) -> Decimal:
    """Costo unitario con 4 decimales (`ROUND_HALF_UP`)."""
    return value.quantize(UNIT, rounding=ROUND_HALF_UP, context=_CONTEXT)


def line_value(quantity: Decimal, unit_cost: Decimal) -> Decimal:
    """`round(quantity × unit_cost, 2)`: valor de una capa, un consumo o una entrada."""
    return money(_CONTEXT.multiply(quantity, unit_cost))


def output_unit_cost(movement_value: Decimal, quantity: Decimal) -> Decimal:
    """Costo unitario informativo de una salida: `movement_value / quantity` con 4 decimales."""
    return unit(_CONTEXT.divide(movement_value, quantity))


def average_unit_cost(inventory_value: Decimal, quantity: Decimal) -> Decimal | None:
    """`inventory_value / quantity` con 4 decimales; nulo sin saldo."""
    if quantity <= 0:
        return None
    return unit(_CONTEXT.divide(inventory_value, quantity))


def inventory_value(layers: Iterable[tuple[Decimal, Decimal]]) -> Decimal:
    """Σ `round(remaining × unit_cost, 2)` de las capas con cantidad restante (recalculado)."""
    total = Decimal("0.00")
    for remaining, unit_cost in layers:
        if remaining > 0:
            total += line_value(remaining, unit_cost)
    return money(total)
