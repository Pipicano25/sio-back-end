"""Cálculos monetarios de las líneas y de la venta (FR-007; research.md R-17).

`Decimal` con `ROUND_HALF_UP`. Las cantidades y precios unitarios caben en
`NUMERIC(18,4)` (< 10^14) y los montos en `NUMERIC(18,2)` (< 10^16). El precio
unitario nunca lo envía el cliente: es el resuelto por Commercial Relationship (DS-11).
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


def check_unit_price(value: Decimal, *, field: str = "unit_price") -> Decimal:
    """Precio resuelto (≥ 0, 4 decimales tras la conversión P-04)."""
    if value < 0:
        raise DomainRuleError("AMOUNT_OUT_OF_RANGE", "El precio unitario no puede ser negativo.", field=field)
    if value >= MAX_QUANTITY:
        raise DomainRuleError("AMOUNT_OUT_OF_RANGE", "El precio unitario está fuera del rango permitido.", field=field)
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
class LineInputs:
    quantity: Decimal
    discount_amount: Decimal
    tax_amount: Decimal


def check_line_inputs(
    quantity: Decimal, discount_amount: Decimal, tax_amount: Decimal, *, prefix: str = ""
) -> LineInputs:
    """Formato de lo que envía el vendedor, antes de conocer el precio (R-07)."""
    return LineInputs(
        check_quantity(quantity, field=f"{prefix}quantity"),
        check_amount(discount_amount, field=f"{prefix}discount_amount"),
        check_amount(tax_amount, field=f"{prefix}tax_amount"),
    )


@dataclass(frozen=True, slots=True)
class LineAmounts:
    quantity: Decimal
    unit_price: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    subtotal: Decimal
    total: Decimal


def line_amounts(
    quantity: Decimal, unit_price: Decimal, discount_amount: Decimal, tax_amount: Decimal, *, prefix: str = ""
) -> LineAmounts:
    """Valida y calcula una línea: `subtotal = round(q × p, 2)`, `total = subtotal − descuento + impuesto`."""
    inputs = check_line_inputs(quantity, discount_amount, tax_amount, prefix=prefix)
    quantity, discount_amount, tax_amount = inputs.quantity, inputs.discount_amount, inputs.tax_amount
    unit_price = check_unit_price(unit_price, field=f"{prefix}quantity")
    subtotal = money(quantity * unit_price)

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

    return LineAmounts(quantity, unit_price, discount_amount, tax_amount, subtotal, total)


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
        raise DomainRuleError("AMOUNT_OUT_OF_RANGE", "Los totales de la venta están fuera del rango permitido.")

    return Totals(money(subtotal), money(discount), money(tax), money(total))
