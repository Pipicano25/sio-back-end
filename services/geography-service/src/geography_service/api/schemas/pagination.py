"""Schemas HTTP compartidos para respuestas paginadas."""

from typing import Generic, TypeVar

from pydantic import BaseModel


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Representa una respuesta HTTP paginada.

    Attributes:
        items: Elementos contenidos en la página actual.
        page: Página solicitada.
        page_size: Cantidad máxima de elementos por página.
        total_records: Cantidad total de registros.
        total_pages: Cantidad total de páginas.
    """

    items: list[T]
    page: int
    page_size: int
    total_records: int
    total_pages: int