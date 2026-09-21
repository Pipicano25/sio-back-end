"""Schemas HTTP compartidos para respuestas paginadas."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Representa una respuesta HTTP paginada."""

    items: list[T]
    page: int
    page_size: int
    total_records: int
    total_pages: int