"""Tipos de operación y de movimiento y su efecto sobre el saldo (§9.2, R-05; 013 R-02)."""

from __future__ import annotations

from decimal import Decimal

ENTRY = "ENTRY"
OUTPUT = "OUTPUT"
ENTRY_REVERSAL = "ENTRY_REVERSAL"
OUTPUT_REVERSAL = "OUTPUT_REVERSAL"
ADJUSTMENT = "ADJUSTMENT"
OPERATION_TYPES = (ENTRY, OUTPUT, ENTRY_REVERSAL, OUTPUT_REVERSAL, ADJUSTMENT)

PURCHASE_ENTRY = "PURCHASE_ENTRY"
SALE_OUTPUT = "SALE_OUTPUT"
MOVEMENT_ENTRY_REVERSAL = "ENTRY_REVERSAL"
MOVEMENT_OUTPUT_REVERSAL = "OUTPUT_REVERSAL"
POSITIVE_ADJUSTMENT = "POSITIVE_ADJUSTMENT"
NEGATIVE_ADJUSTMENT = "NEGATIVE_ADJUSTMENT"

PURCHASE = "PURCHASE"
SALE = "SALE"
ORIGIN_ADJUSTMENT = "ADJUSTMENT"
ORIGIN_COUNT = "COUNT"

MOVEMENT_TYPE_BY_OPERATION = {
    ENTRY: PURCHASE_ENTRY,
    OUTPUT: SALE_OUTPUT,
    ENTRY_REVERSAL: MOVEMENT_ENTRY_REVERSAL,
    OUTPUT_REVERSAL: MOVEMENT_OUTPUT_REVERSAL,
}
"""Tipo de movimiento por defecto de las operaciones de la Fase A (los ajustes lo traen por línea)."""

ORIGIN_TYPE_BY_OPERATION = {
    ENTRY: PURCHASE,
    OUTPUT: SALE,
    ENTRY_REVERSAL: PURCHASE,
    OUTPUT_REVERSAL: SALE,
}

REVERSAL_OF = {ENTRY: ENTRY_REVERSAL, OUTPUT: OUTPUT_REVERSAL}
"""Tipo del reverso de cada operación original."""

_SIGN = {
    PURCHASE_ENTRY: 1,
    MOVEMENT_OUTPUT_REVERSAL: 1,
    POSITIVE_ADJUSTMENT: 1,
    SALE_OUTPUT: -1,
    MOVEMENT_ENTRY_REVERSAL: -1,
    NEGATIVE_ADJUSTMENT: -1,
}

CREATES_LAYER = frozenset({PURCHASE_ENTRY, POSITIVE_ADJUSTMENT})
CONSUMES_LAYERS = frozenset({SALE_OUTPUT, NEGATIVE_ADJUSTMENT})


def is_reversal(operation_type: str) -> bool:
    return operation_type in (ENTRY_REVERSAL, OUTPUT_REVERSAL)


def apply_movement(balance: Decimal, movement_type: str, quantity: Decimal) -> Decimal:
    """Saldo nuevo tras un movimiento (puede ser negativo: lo rechaza quien llama)."""
    return balance + _SIGN[movement_type] * quantity
