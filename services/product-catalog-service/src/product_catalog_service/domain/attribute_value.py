"""Validación de valores tipados de atributos (FR-046, FR-047, RC-05)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from product_catalog_service.domain.completeness import VALUE_FIELD_BY_DATA_TYPE

VALUE_FIELDS = tuple(VALUE_FIELD_BY_DATA_TYPE.values())
INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1
MAX_INTEGER_DIGITS = 10
MAX_DECIMAL_PLACES = 8


class ValueTypeMismatch(ValueError):
    """El dato enviado no corresponde al tipo de la definición."""


def validate_typed_value(data_type: str, payload: dict[str, Any]) -> tuple[str, Any]:
    """Devuelve `(campo, valor)` o lanza `ValueTypeMismatch`.

    Exige exactamente un dato informado y que sea el campo del `data_type`.
    """
    provided = {name: value for name, value in payload.items() if name in VALUE_FIELDS and value is not None}

    if len(provided) != 1:
        raise ValueTypeMismatch("Debe informarse exactamente un dato del atributo.")

    field, value = next(iter(provided.items()))
    expected = VALUE_FIELD_BY_DATA_TYPE.get(data_type)
    if field != expected:
        raise ValueTypeMismatch(f"El atributo es de tipo {data_type}: use {expected}.")

    if data_type == "TEXT":
        if not isinstance(value, str) or not value.strip():
            raise ValueTypeMismatch("El texto no puede estar vacío.")
        return field, value.strip()

    if data_type == "INTEGER":
        if isinstance(value, bool) or not isinstance(value, int) or not INT64_MIN <= value <= INT64_MAX:
            raise ValueTypeMismatch("El entero debe ser de hasta 64 bits.")
        return field, value

    if data_type == "DECIMAL":
        number = value if isinstance(value, Decimal) else Decimal(str(value))
        if not number.is_finite():
            raise ValueTypeMismatch("El decimal debe ser finito.")
        sign, digits, exponent = number.as_tuple()
        decimals = max(0, -exponent)
        integer_digits = max(0, len(digits) + exponent)
        if decimals > MAX_DECIMAL_PLACES or integer_digits > MAX_INTEGER_DIGITS:
            raise ValueTypeMismatch("El decimal admite hasta 10 dígitos enteros y 8 decimales.")
        return field, number

    if data_type == "BOOLEAN":
        if not isinstance(value, bool):
            raise ValueTypeMismatch("El valor debe ser verdadero o falso.")
        return field, value

    if data_type == "DATE":
        if not isinstance(value, date):
            raise ValueTypeMismatch("El valor debe ser una fecha de calendario.")
        return field, value

    if data_type == "OPTION":
        if not isinstance(value, UUID):
            raise ValueTypeMismatch("El valor debe ser el identificador de una opción.")
        return field, value

    raise ValueTypeMismatch(f"Tipo de dato desconocido: {data_type}.")
