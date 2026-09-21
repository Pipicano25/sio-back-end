"""Tipos compartidos de paginación de la capa de aplicación."""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class PageResult(Generic[T]):
    """Representa el resultado paginado de una consulta.

    Attributes:
        items: Registros contenidos en la página.
        page: Página solicitada.
        page_size: Cantidad máxima de registros por página.
        total_records: Total de registros después de aplicar filtros.
    """

    items: list[T]
    page: int
    page_size: int
    total_records: int

    @property
    def total_pages(self) -> int:
        """Calcula el número total de páginas.

        Returns:
            Total de páginas disponibles para el resultado filtrado.
        """
        if self.total_records == 0:
            return 0

        return (
            self.total_records + self.page_size - 1
        ) // self.page_size