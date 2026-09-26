"""Resultado paginado de la capa de aplicación."""

from dataclasses import dataclass
from math import ceil
from typing import Generic, TypeVar

ItemT = TypeVar("ItemT")


@dataclass(frozen=True, slots=True)
class PageResult(Generic[ItemT]):
    """Página de resultados con los totales del formato SIO."""

    items: list[ItemT]
    page: int
    page_size: int
    total_records: int

    @property
    def total_pages(self) -> int:
        """Cantidad de páginas; 0 cuando no hay registros."""
        return ceil(self.total_records / self.page_size) if self.total_records else 0
