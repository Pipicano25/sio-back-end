"""Cálculo del precio automático por recepción de compras (spec 021: FR-021-21, FR-021-23, RC-021-7).

Funciones puras, sin base de datos:

- **Costo real unitario** (B-1, B-2): `total pagado de la línea / cantidad`, donde el total ya incluye el impuesto y
  descuenta el descuento. No se suma ningún impuesto más.
- **Referencia**: si el costo actual es mayor o igual al anterior (o no hay anterior), el actual; si es menor, el
  promedio aritmético simple de los dos costos reales.
- **Precio**: `referencia × (1 + recargo / 100)`, redondeado una sola vez con `ROUND_HALF_UP` a los decimales de la
  moneda de la lista.

Toda la aritmética usa `decimal` con 28 dígitos significativos; nunca punto flotante ni redondeos intermedios.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal
from enum import Enum

from commercial_relationship_service.domain.currency import currency_places

CONTEXT = Context(prec=28, rounding=ROUND_HALF_UP)
HUNDRED = Decimal(100)
TWO = Decimal(2)


def real_unit_cost(line_total: Decimal, quantity: Decimal) -> Decimal:
    """Costo real por unidad de la presentación: total pagado de la línea / cantidad.

    Raises:
        ValueError: Si la cantidad no es positiva.
    """
    if quantity <= 0:
        raise ValueError("La cantidad de la línea debe ser positiva.")
    return CONTEXT.divide(line_total, quantity)


def reference_cost(current: Decimal, previous: Decimal | None) -> Decimal:
    """Costo comercial de referencia frente a la recepción inmediatamente anterior (costos reales)."""
    if previous is None or current >= previous:
        return current
    return CONTEXT.divide(CONTEXT.add(previous, current), TWO)


def final_price(reference: Decimal, markup_percentage: Decimal, currency_code: str) -> Decimal:
    """Precio de venta: único redondeo `ROUND_HALF_UP` a los decimales de la moneda."""
    factor = CONTEXT.add(Decimal(1), CONTEXT.divide(markup_percentage, HUNDRED))
    raw = CONTEXT.multiply(reference, factor)
    return raw.quantize(Decimal(1).scaleb(-currency_places(currency_code)), rounding=ROUND_HALF_UP)


class Outcome(str, Enum):
    """Resultado final de una aplicación (estados de `automatic_price_applications`)."""

    APPLIED = "APPLIED"
    UNCHANGED = "UNCHANGED"
    # Aclaración del 2026-10-16 (RC-021-13): sin política no se toca ningún precio de la lista y presentación.
    SKIPPED_NO_POLICY = "SKIPPED_NO_POLICY"
    SKIPPED_LIST_NOT_EFFECTIVE = "SKIPPED_LIST_NOT_EFFECTIVE"
    SKIPPED_CURRENCY_MISMATCH = "SKIPPED_CURRENCY_MISMATCH"
    SKIPPED_PRESENTATION_INACTIVE = "SKIPPED_PRESENTATION_INACTIVE"
    SKIPPED_ZERO_COST = "SKIPPED_ZERO_COST"


@dataclass(frozen=True, slots=True)
class PriceEvaluation:
    """Hechos que decide el resultado de una aplicación (FR-021-23).

    Attributes:
        list_effective: La lista está `ACTIVE` y vigente al procesar (M-4).
        currency_matches: La moneda de la lista es la de la compra (sin conversión).
        presentation_active: La presentación está `ACTIVE`.
        current_unit_cost: Costo real unitario de la recepción.
        has_policy: La captura en `received_at` tiene política para la presentación en esta lista.
        current_price: Precio vigente, o `None` si no hay.
        has_future_prices: Hay precios futuros `ACTIVE` para esta lista y presentación.
        new_price: Precio calculado (solo con política).
    """

    list_effective: bool
    currency_matches: bool
    presentation_active: bool
    current_unit_cost: Decimal
    has_policy: bool
    current_price: Decimal | None
    has_future_prices: bool
    new_price: Decimal | None


def decide(evaluation: PriceEvaluation) -> Outcome:
    """Aplica el orden estable de FR-021-23 y devuelve el resultado de la aplicación."""
    if not evaluation.list_effective:
        return Outcome.SKIPPED_LIST_NOT_EFFECTIVE
    if not evaluation.currency_matches:
        return Outcome.SKIPPED_CURRENCY_MISMATCH
    if not evaluation.presentation_active:
        return Outcome.SKIPPED_PRESENTATION_INACTIVE
    if evaluation.current_unit_cost <= 0:
        return Outcome.SKIPPED_ZERO_COST
    if not evaluation.has_policy:
        return Outcome.SKIPPED_NO_POLICY
    if evaluation.current_price is not None and evaluation.current_price == evaluation.new_price:
        return Outcome.UNCHANGED
    return Outcome.APPLIED
