"""Cálculos monetarios de las líneas y de la compra (FR-006, FR-007; research.md R-11).

`Decimal` con `ROUND_HALF_UP`. Las cantidades y costos unitarios caben en
`NUMERIC(18,4)` (< 10^14) y los montos en `NUMERIC(18,2)` (< 10^16).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

MONEY_QUANTUM = Decimal("0.01")
QUANTITY_QUANTUM = Decimal("0.0001")
FACTOR_QUANTUM = Decimal("0.00000001")
MAX_QUANTITY = Decimal(10) ** 14
MAX_MONEY = Decimal(10) ** 16


class DomainRuleError(ValueError):
    """Regla de dominio incumplida; `code` es la causa de `errors[].code` (`422`)."""

    def __init__(self, code: str, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field


def decimal_places(value: Decimal) -> int:
    exponent = value.normalize().as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else 0


def to_decimal(value: object) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DomainRuleError("INVALID_FORMAT", "El valor no es un número decimal válido.") from None
    if not parsed.is_finite():
        raise DomainRuleError("INVALID_FORMAT", "El valor no es un número decimal válido.")
    return parsed


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def check_quantity(value: Decimal, *, field: str = "quantity") -> Decimal:
    if value <= 0:
        raise DomainRuleError("QUANTITY_NOT_POSITIVE", "La cantidad debe ser mayor que cero.", field=field)
    if decimal_places(value) > 4:
        raise DomainRuleError("TOO_MANY_DECIMALS", "La cantidad admite a lo sumo 4 decimales.", field=field)
    if value >= MAX_QUANTITY:
        raise DomainRuleError("AMOUNT_OUT_OF_RANGE", "La cantidad está fuera del rango permitido.", field=field)
    return value.quantize(QUANTITY_QUANTUM)


def check_unit_cost(value: Decimal, *, field: str = "unit_cost") -> Decimal:
    if value < 0:
        raise DomainRuleError("AMOUNT_OUT_OF_RANGE", "El costo unitario no puede ser negativo.", field=field)
    if decimal_places(value) > 4:
        raise DomainRuleError("TOO_MANY_DECIMALS", "El costo unitario admite a lo sumo 4 decimales.", field=field)
    if value >= MAX_QUANTITY:
        raise DomainRuleError("AMOUNT_OUT_OF_RANGE", "El costo unitario está fuera del rango permitido.", field=field)
    return value.quantize(QUANTITY_QUANTUM)


def check_amount(value: Decimal, *, field: str) -> Decimal:
    if value < 0:
        raise DomainRuleError("AMOUNT_OUT_OF_RANGE", "El monto no puede ser negativo.", field=field)
    if decimal_places(value) > 2:
        raise DomainRuleError("TOO_MANY_DECIMALS", "El monto admite a lo sumo 2 decimales.", field=field)
    if value >= MAX_MONEY:
        raise DomainRuleError("AMOUNT_OUT_OF_RANGE", "El monto está fuera del rango permitido.", field=field)
    return value.quantize(MONEY_QUANTUM)


@dataclass(frozen=True, slots=True)
class LineAmounts:
    quantity: Decimal
    unit_cost: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    subtotal: Decimal
    total: Decimal


def line_amounts(
    quantity: Decimal, unit_cost: Decimal, discount_amount: Decimal, tax_amount: Decimal, *, prefix: str = ""
) -> LineAmounts:
    """Valida y calcula una línea: `subtotal = round(q × c, 2)`, `total = subtotal − descuento + impuesto`."""
    quantity = check_quantity(quantity, field=f"{prefix}quantity")
    unit_cost = check_unit_cost(unit_cost, field=f"{prefix}unit_cost")
    discount_amount = check_amount(discount_amount, field=f"{prefix}discount_amount")
    tax_amount = check_amount(tax_amount, field=f"{prefix}tax_amount")
    subtotal = money(quantity * unit_cost)

    if subtotal >= MAX_MONEY:
        raise DomainRuleError(
            "AMOUNT_OUT_OF_RANGE", "El subtotal de la línea está fuera del rango permitido.", field=f"{prefix}quantity"
        )
    if discount_amount > subtotal:
        raise DomainRuleError(
            "DISCOUNT_EXCEEDS_SUBTOTAL",
            "El descuento no puede ser mayor que el subtotal de la línea.",
            field=f"{prefix}discount_amount",
        )

    total = subtotal - discount_amount + tax_amount

    if total >= MAX_MONEY:
        raise DomainRuleError(
            "AMOUNT_OUT_OF_RANGE", "El total de la línea está fuera del rango permitido.", field=f"{prefix}tax_amount"
        )

    return LineAmounts(quantity, unit_cost, discount_amount, tax_amount, subtotal, total)


@dataclass(frozen=True, slots=True)
class Totals:
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal


ZERO_TOTALS = Totals(Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))


def header_totals(lines: Iterable[tuple[Decimal, Decimal, Decimal]]) -> Totals:
    """Totales de la cabecera a partir de `(subtotal, descuento, impuesto)` de cada línea."""
    subtotal = discount = tax = Decimal("0.00")

    for line_subtotal, line_discount, line_tax in lines:
        subtotal += line_subtotal
        discount += line_discount
        tax += line_tax

    total = subtotal - discount + tax

    if max(subtotal, total) >= MAX_MONEY:
        raise DomainRuleError("AMOUNT_OUT_OF_RANGE", "Los totales de la compra están fuera del rango permitido.")

    return Totals(money(subtotal), money(discount), money(tax), money(total))
