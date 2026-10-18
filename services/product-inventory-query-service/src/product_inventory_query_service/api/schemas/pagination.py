"""Sobre de respuesta de los listados paginados por cursor (FR-022-05, FR-022-60; A-20).

Sin `total_records`, `total_pages` ni `page`: el servicio no calcula conteos de coincidencias.
"""

from __future__ import annotations

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

ResetReason = Literal["FILTERS_CHANGED", "SORT_CHANGED", "PAGE_SIZE_CHANGED", "CURSOR_EXPIRED"]


class CursorPage(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="forbid")

    items: list[T]
    page_size: int
    has_next: bool
    next_cursor: str | None
    pagination_reset: bool
    pagination_reset_reason: ResetReason | None
    partial: bool
    partial_reason: Literal["WORK_LIMIT_REACHED"] | None
    sort_applied: str
    resolved_at: datetime
