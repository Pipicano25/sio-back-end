"""Utilidades comunes de las escrituras de la Fase B (auditoría y `PUT` idéntico)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any


def same_value(current: Any, new: Any) -> bool:
    """Comparación semántica: importes por valor decimal (FR-072, `PUT` idéntico)."""
    if current is None or new is None:
        return current is new

    if isinstance(current, Decimal) or isinstance(new, Decimal):
        return Decimal(current) == Decimal(new)

    return current == new


def unchanged(model: Any, values: dict[str, Any]) -> bool:
    """Indica si aplicar `values` no cambia nada del registro."""
    return all(same_value(getattr(model, name), value) for name, value in values.items())


def touch(model: Any, actor: str) -> None:
    """Auditoría de una modificación persistente (Principio VI)."""
    model.updated_by = actor
    model.updated_at = datetime.now(UTC)
