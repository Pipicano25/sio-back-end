"""Tipos de operación y de movimiento y su efecto sobre el saldo (§9.2, R-05)."""

from __future__ import annotations

from decimal import Decimal

ENTRY = "ENTRY"
OUTPUT = "OUTPUT"
ENTRY_REVERSAL = "ENTRY_REVERSAL"
OUTPUT_REVERSAL = "OUTPUT_REVERSAL"
OPERATION_TYPES = (ENTRY, OUTPUT, ENTRY_REVERSAL, OUTPUT_REVERSAL)

PURCHASE_ENTRY = "PURCHASE_ENTRY"
SALE_OUTPUT = "SALE_OUTPUT"
MOVEMENT_ENTRY_REVERSAL = "ENTRY_REVERSAL"
MOVEMENT_OUTPUT_REVERSAL = "OUTPUT_REVERSAL"

PURCHASE = "PURCHASE"
SALE = "SALE"

MOVEMENT_TYPE_BY_OPERATION = {
    ENTRY: PURCHASE_ENTRY,
    OUTPUT: SALE_OUTPUT,
    ENTRY_REVERSAL: MOVEMENT_ENTRY_REVERSAL,
    OUTPUT_REVERSAL: MOVEMENT_OUTPUT_REVERSAL,
}

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
    SALE_OUTPUT: -1,
    MOVEMENT_ENTRY_REVERSAL: -1,
}


def is_reversal(operation_type: str) -> bool:
    return operation_type in (ENTRY_REVERSAL, OUTPUT_REVERSAL)


def apply_movement(balance: Decimal, movement_type: str, quantity: Decimal) -> Decimal:
    """Saldo nuevo tras un movimiento (puede ser negativo: lo rechaza quien llama)."""
    return balance + _SIGN[movement_type] * quantity


def is_unit_cost_allowed(movement_type: str) -> bool:
    """`unit_cost` solo en entradas de compra y sus reversos (FR-018)."""
    return movement_type in (PURCHASE_ENTRY, MOVEMENT_ENTRY_REVERSAL)
