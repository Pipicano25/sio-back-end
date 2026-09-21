"""Modelos compartidos para resultados paginados."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PageResult(Generic[T]):
    """Representa una página de resultados.

    Attributes:
        items: Registros incluidos en la página actual.
        page: Número de página actual.
        page_size: Cantidad máxima de registros por página.
        total_records: Cantidad total de registros existentes.
    """

    items: list[T]
    page: int
    page_size: int
    total_records: int

    @property
    def total_pages(self) -> int:
        """Calcula la cantidad total de páginas.

        Returns:
            Cantidad de páginas disponibles para el tamaño solicitado.
        """
        if self.total_records == 0:
            return 0

        return (
            self.total_records
            + self.page_size
            - 1
        ) // self.page_size
