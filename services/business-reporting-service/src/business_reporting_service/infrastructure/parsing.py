"""Lectura estricta de los cuerpos de los propietarios: un campo ausente o de otro tipo es `UnexpectedBody` → `503`."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID


class UnexpectedBody(Exception):
    """El cuerpo no cumple el contrato del propietario."""


def obj(value: Any) -> dict:
    if not isinstance(value, dict):
        raise UnexpectedBody("se esperaba un objeto")
    return value


def items(value: Any, key: str = "items") -> list[dict]:
    found = obj(value).get(key)
    if not isinstance(found, list):
        raise UnexpectedBody(f"se esperaba la lista {key}")
    return [obj(item) for item in found]


def uuid_of(value: dict, key: str, *, optional: bool = False) -> UUID | None:
    raw = value.get(key)
    if raw is None and optional:
        return None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        raise UnexpectedBody(key) from None


def text_of(value: dict, key: str, *, optional: bool = False) -> str | None:
    raw = value.get(key)
    if raw is None and optional:
        return None
    if not isinstance(raw, str):
        raise UnexpectedBody(key)
    return raw


def int_of(value: dict, key: str) -> int:
    raw = value.get(key)
    if not isinstance(raw, int) or isinstance(raw, bool):
        raise UnexpectedBody(key)
    return raw


def bool_of(value: dict, key: str) -> bool:
    raw = value.get(key)
    if not isinstance(raw, bool):
        raise UnexpectedBody(key)
    return raw


def decimal_of(value: dict, key: str) -> Decimal:
    raw = value.get(key)
    if not isinstance(raw, (str, int)) or isinstance(raw, bool):
        raise UnexpectedBody(key)
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        raise UnexpectedBody(key) from None


def date_of(value: dict, key: str) -> date:
    try:
        return date.fromisoformat(str(value.get(key)))
    except ValueError:
        raise UnexpectedBody(key) from None


def datetime_of(value: dict, key: str, *, optional: bool = False) -> datetime | None:
    raw = value.get(key)
    if raw is None and optional:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        raise UnexpectedBody(key) from None
