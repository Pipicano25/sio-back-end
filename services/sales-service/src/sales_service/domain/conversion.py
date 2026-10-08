"""Conversión a unidad base y del precio a la unidad de venta (FR-018, DS-03, DS-04, P-04; research.md R-07, R-09).

- `base_quantity = quantity × factor`, exacta y con a lo sumo 4 decimales
  (Inventory exige cantidades en unidad base con ≤ 4 decimales).
- Precio resuelto por Commercial Relationship (`basis`): `PRESENTATION` se usa tal cual;
  `BASE_UNIT` en una línea con presentación se multiplica por el factor y se redondea
  `ROUND_HALF_UP` a **4 decimales** (P-04, consistente con `unit_price NUMERIC(18,4)`).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sales_service.domain.money import (
    MAX_QUANTITY,
    QUANTITY_QUANTUM,
    DomainRuleError,
    decimal_places,
)

DEFAULT_FACTOR = Decimal("1")
PRESENTATION = "PRESENTATION"
BASE_UNIT = "BASE_UNIT"
PRICE_BASES = (PRESENTATION, BASE_UNIT)


def check_factor(factor: Decimal) -> Decimal:
    if factor <= 0 or decimal_places(factor) > 8:
        raise DomainRuleError("INVALID_FORMAT", "El factor de la presentación es inválido.")
    return factor


def base_quantity(quantity: Decimal, factor: Decimal, *, field: str = "quantity") -> Decimal:
    """Cantidad en unidad base; rechaza la que necesitaría más de 4 decimales."""
    product = quantity * check_factor(factor)

    if decimal_places(product) > 4:
        raise DomainRuleError(
            "BASE_QUANTITY_PRECISION",
            "La cantidad convertida a la unidad base necesita más de 4 decimales.",
            field=field,
        )
    if product >= MAX_QUANTITY:
        raise DomainRuleError(
            "AMOUNT_OUT_OF_RANGE", "La cantidad en unidad base está fuera del rango permitido.", field=field
        )

    return product.quantize(QUANTITY_QUANTUM)


def sale_unit_price(price: Decimal, basis: str, factor: Decimal) -> Decimal:
    """Precio por unidad de venta a partir del precio resuelto y su base (DS-04, P-04)."""
    if basis == PRESENTATION:
        return price.quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)
    if basis == BASE_UNIT:
        return (price * check_factor(factor)).quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)
    raise ValueError(f"Base de precio desconocida: {basis}")
