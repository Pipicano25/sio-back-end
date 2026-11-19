"""`PUT` parcial (constitución 4.0.0, D28): combina lo enviado con lo guardado."""

from __future__ import annotations

from dataclasses import fields
from typing import Any, TypeVar

T = TypeVar("T")


def merge(data_class: type[T], current: Any, changes: dict[str, Any], **defaults: Any) -> T:
    """Construye `data_class` con los campos enviados y, para el resto, el valor guardado.

    `defaults` reemplaza el valor guardado de un campo no enviado (p. ej. una tasa
    que solo se conserva si fue un ajuste de la línea).
    """
    values = {}
    for field in fields(data_class):
        if field.name in changes:
            values[field.name] = changes[field.name]
        elif field.name in defaults:
            values[field.name] = defaults[field.name]
        else:
            values[field.name] = getattr(current, field.name)
    return data_class(**values)
