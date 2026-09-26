"""Paginación de consultas en la capa de aplicación."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PageResult(Generic[T]):
    """Página de resultados."""

    items: list[T]
    page: int
    page_size: int
    total_records: int

    @property
    def total_pages(self) -> int:
        return math.ceil(self.total_records / self.page_size) if self.total_records else 0


def paginate(
    session: Session,
    statement: Select,
    *,
    page: int,
    page_size: int,
) -> PageResult:
    """Ejecuta una consulta paginada sobre entidades ORM."""
    total = session.execute(
        select(func.count()).select_from(statement.order_by(None).subquery())
    ).scalar_one()

    items = list(
        session.execute(
            statement.limit(page_size).offset((page - 1) * page_size)
        ).scalars()
    )

    return PageResult(items=items, page=page, page_size=page_size, total_records=total)
