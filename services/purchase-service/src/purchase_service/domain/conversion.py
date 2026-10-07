"""Conversión a unidad base y costo para Inventory (FR-019, DS-03, DS-04; research.md R-07).

- `base_quantity = quantity × factor`, exacta y con a lo sumo 4 decimales
  (Inventory exige cantidades en unidad base con ≤ 4 decimales).
- `inventory_unit_cost = ROUND_HALF_UP((subtotal − descuento) / base_quantity, 4)`,
  **sin impuestos** (se consideran recuperables).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from purchase_service.domain.money import (
    MAX_QUANTITY,
    QUANTITY_QUANTUM,
    DomainRuleError,
    decimal_places,
)

DEFAULT_FACTOR = Decimal("1")


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


def inventory_unit_cost(subtotal: Decimal, discount_amount: Decimal, base_qty: Decimal) -> Decimal:
    """Costo por unidad base que Purchase informa a Inventory (DS-04)."""
    return ((subtotal - discount_amount) / base_qty).quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)
