"""Numeración oficial por período (FR-026, DS-08; research.md R-03).

Cada secuencia lleva un contador independiente por período, determinado por la
`operation_date` de la venta:

| `reset_policy` | `period_key` | Número |
| --- | --- | --- |
| `NEVER` | `''` | `FV-000001` |
| `YEARLY` | `'2026'` | `FV-2026-000001` |
| `MONTHLY` | `'202610'` | `FV-202610-000001` |
"""

from __future__ import annotations

from datetime import date

NEVER = "NEVER"
YEARLY = "YEARLY"
MONTHLY = "MONTHLY"
RESET_POLICIES = (NEVER, YEARLY, MONTHLY)
SEPARATORS = ("-", "/", ".", "_", "")
MAX_NUMBER_TEXT = 80
PERIOD_MAX_LENGTH = 6


def period_key(reset_policy: str, operation_date: date) -> str:
    if reset_policy == NEVER:
        return ""
    if reset_policy == YEARLY:
        return f"{operation_date.year:04d}"
    if reset_policy == MONTHLY:
        return f"{operation_date.year:04d}{operation_date.month:02d}"
    raise ValueError(f"reset_policy desconocida: {reset_policy}")


def format_number(prefix: str, separator: str, period: str, value: int, number_length: int) -> str:
    """`prefix + separator + [period + separator] + número con ceros a la izquierda`."""
    digits = str(value).rjust(number_length, "0")
    middle = f"{period}{separator}" if period else ""
    return f"{prefix}{separator}{middle}{digits}"


def max_number_text_length(prefix: str, separator: str, number_length: int) -> int:
    """Longitud máxima posible del número de una secuencia (debe ser ≤ 80)."""
    return len(prefix) + 2 * len(separator) + PERIOD_MAX_LENGTH + number_length


def next_value(current: int | None, initial_number: int) -> int:
    return initial_number if current is None else current + 1


def exceeds_maximum(value: int, maximum_number: int | None, number_length: int) -> bool:
    """El valor supera `maximum_number` o ya no cabe en `number_length` dígitos."""
    if maximum_number is not None and value > maximum_number:
        return True
    return len(str(value)) > number_length
