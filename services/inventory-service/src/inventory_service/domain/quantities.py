"""Cantidades y costos de inventario (`NUMERIC(18,4)`; R-10, FR-018).

Las cantidades se reciben como cadena decimal o entero, se guardan con 4
decimales y viajan en las respuestas como cadena con exactamente 4 decimales.
La forma normalizada (sin ceros a la derecha) es la que entra en la huella de la
solicitud (R-03): `"10"`, `"10.0"` y `"10.0000"` son la misma cantidad.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

SCALE = 4
MAX_ABS = Decimal("1e14")
"""Límite exclusivo de `NUMERIC(18,4)`: 14 dígitos enteros."""

_QUANTUM = Decimal(1).scaleb(-SCALE)


class QuantityError(ValueError):
    """Valor decimal inválido; `code` es la causa de `contracts/errors.md`."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _to_decimal(value: Any) -> Decimal:
    if isinstance(value, bool) or value is None:
        raise QuantityError("INVALID_FORMAT", "Debe ser un número decimal.")

    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, int):
        number = Decimal(value)
    elif isinstance(value, float):
        number = Decimal(str(value))
    elif isinstance(value, str) and value.strip():
        try:
            number = Decimal(value.strip())
        except InvalidOperation:
            raise QuantityError("INVALID_FORMAT", "Debe ser un número decimal.") from None
    else:
        raise QuantityError("INVALID_FORMAT", "Debe ser un número decimal.")

    if not number.is_finite():
        raise QuantityError("INVALID_FORMAT", "Debe ser un número decimal finito.")

    return number


def _check_scale_and_range(number: Decimal) -> Decimal:
    if number != number.quantize(_QUANTUM):
        raise QuantityError("TOO_MANY_DECIMALS", f"Admite a lo sumo {SCALE} decimales.")

    if abs(number) >= MAX_ABS:
        raise QuantityError("QUANTITY_OUT_OF_RANGE", "El valor supera el máximo permitido.")

    return number


def parse_quantity(value: Any) -> Decimal:
    """Cantidad en unidad base: > 0, a lo sumo 4 decimales y dentro de `NUMERIC(18,4)`."""
    number = _to_decimal(value)

    if number <= 0:
        raise QuantityError("QUANTITY_NOT_POSITIVE", "La cantidad debe ser mayor que cero.")

    return _check_scale_and_range(number)


def parse_unit_cost(value: Any) -> Decimal:
    """Costo unitario de una entrada: ≥ 0, a lo sumo 4 decimales (FR-018)."""
    number = _to_decimal(value)

    if number < 0:
        raise QuantityError("UNIT_COST_NEGATIVE", "El costo unitario no puede ser negativo.")

    return _check_scale_and_range(number)


def in_range(number: Decimal) -> bool:
    """Indica si un saldo resultante es representable en `NUMERIC(18,4)`."""
    return abs(number) < MAX_ABS


def normalize_decimal(number: Decimal) -> str:
    """Forma canónica sin ceros a la derecha ni exponente (`10`, `5.5`)."""
    normalized = number.normalize()

    if normalized == 0:
        return "0"

    text = format(normalized, "f")
    return text


def format_decimal(number: Decimal) -> str:
    """Representación de respuesta con exactamente 4 decimales (`"10.0000"`)."""
    return format(number.quantize(_QUANTUM), "f")


def format_money(number: Decimal) -> str:
    """Valor monetario de respuesta con exactamente 2 decimales (`"12600.00"`; 013 R-04)."""
    return format(number.quantize(Decimal("0.01")), "f")


def optional_decimal(number: Decimal | None) -> str | None:
    return format_decimal(number) if number is not None else None


def optional_money(number: Decimal | None) -> str | None:
    return format_money(number) if number is not None else None


def parse_decimal(value: Any) -> Decimal:
    """Decimal con a lo sumo 4 decimales dentro de `NUMERIC(18,4)`, sin restricción de signo (niveles de políticas)."""
    return _check_scale_and_range(_to_decimal(value))
