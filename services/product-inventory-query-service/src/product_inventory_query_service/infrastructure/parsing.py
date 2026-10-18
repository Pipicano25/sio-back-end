"""Lectura estricta de las respuestas de las dependencias: un cuerpo inesperado nunca se interpreta como vacío."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID


class UnexpectedBody(Exception):
    """El cuerpo no tiene la forma del contrato; el adaptador lo traduce a `503`."""


def obj(value: Any) -> dict:
    if not isinstance(value, dict):
        raise UnexpectedBody("objeto")
    return value


def items(body: Any, key: str = "items") -> list[dict]:
    value = obj(body).get(key)
    if not isinstance(value, list):
        raise UnexpectedBody(key)
    return [obj(item) for item in value]


def uuid_of(data: dict, key: str, *, optional: bool = False) -> UUID | None:
    value = data.get(key)
    if value is None and optional:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        raise UnexpectedBody(key) from None


def text_of(data: dict, key: str, *, optional: bool = False) -> str | None:
    value = data.get(key)
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise UnexpectedBody(key)
    return value


def bool_of(data: dict, key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise UnexpectedBody(key)
    return value


def int_of(data: dict, key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise UnexpectedBody(key)
    return value


def decimal_of(data: dict, key: str) -> Decimal:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise UnexpectedBody(key)
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise UnexpectedBody(key) from None


def datetime_of(data: dict, key: str) -> datetime:
    value = data.get(key)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise UnexpectedBody(key) from None


def position_of(data: dict) -> dict:
    value = obj(data).get("position")
    if not isinstance(value, dict) or "id" not in value:
        raise UnexpectedBody("position")
    return value


def chunks(values: list, size: int = 100) -> list[list]:
    return [values[start:start + size] for start in range(0, len(values), size)]
