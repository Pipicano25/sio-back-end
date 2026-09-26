"""Reglas de la familia GTIN (GTIN, EAN, UPC) según GS1 (R-13, DS-05, DS-17)."""

from __future__ import annotations

GTIN_FAMILY = frozenset({"GTIN", "EAN", "UPC"})
GTIN_LENGTHS = frozenset({8, 12, 13, 14})
CANONICAL_LENGTH = 14


def has_gtin_shape(value: str) -> bool:
    """Indica si el valor es numérico y tiene una longitud GTIN válida."""
    return value.isascii() and value.isdigit() and len(value) in GTIN_LENGTHS


def has_valid_check_digit(value: str) -> bool:
    """Valida el dígito de control GS1 (módulo 10, pesos 3 y 1 desde la derecha)."""
    if not (value.isascii() and value.isdigit()) or len(value) < 2:
        return False

    body = value[:-1]
    total = 0

    for position, char in enumerate(reversed(body)):
        weight = 3 if position % 2 == 0 else 1
        total += int(char) * weight

    expected = (10 - total % 10) % 10
    return expected == int(value[-1])


def is_valid_gtin_format(value: str) -> bool:
    """Numérico, longitud 8/12/13/14 y dígito de control correcto."""
    return has_gtin_shape(value) and has_valid_check_digit(value)


def gtin_canonical(value: str) -> str:
    """Forma canónica de 14 dígitos (ceros a la izquierda)."""
    return value.zfill(CANONICAL_LENGTH)


def canonical_value(identifier_type: str, value: str) -> str:
    """Valor usado para comprobar unicidad según el tipo de identificador."""
    if identifier_type in GTIN_FAMILY:
        return gtin_canonical(value)

    return value
