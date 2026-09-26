"""Filtros de consulta reutilizables (FR-009)."""

from __future__ import annotations

from sqlalchemy import Select, func
from sqlalchemy.sql.elements import ColumnElement

from product_catalog_service.application.normalization import canonical_name_key

_ACCENTED = "áàäâãéèëêíìïîóòöôõúùüûñç"
_PLAIN = "aaaaaeeeeiiiiooooouuuunc"


def folded(column) -> ColumnElement:
    """Columna en minúsculas y sin tildes, para búsquedas parciales."""
    return func.translate(func.lower(column), _ACCENTED, _PLAIN)


def search_pattern(term: str) -> str:
    """Patrón `ILIKE` con el término normalizado igual que `folded`."""
    escaped = canonical_name_key(term).replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
    return f"%{escaped}%"


def apply_common_filters(
    statement: Select,
    model,
    *,
    status: str | None = None,
    code: str | None = None,
    search: str | None = None,
    search_column=None,
) -> Select:
    """Aplica los filtros `status`, `code` (exacto normalizado) y `search` (nombre)."""
    if status is not None and hasattr(model, "status"):
        statement = statement.where(model.status == status)

    if code is not None and hasattr(model, "code"):
        statement = statement.where(model.code == code.strip().upper())

    if search:
        column = search_column if search_column is not None else model.name
        statement = statement.where(folded(column).like(search_pattern(search), escape="\\"))

    return statement
