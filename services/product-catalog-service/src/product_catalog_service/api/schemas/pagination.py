"""Esquema común de respuestas paginadas."""

from collections.abc import Callable
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from product_catalog_service.application.pagination import PageResult

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada estándar de SIO."""

    items: list[T]
    page: int
    page_size: int
    total_records: int
    total_pages: int

    @classmethod
    def from_page(
        cls,
        result: PageResult,
        mapper: Callable[[Any], T],
    ) -> "PaginatedResponse[T]":
        return cls(
            items=[mapper(item) for item in result.items],
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )
