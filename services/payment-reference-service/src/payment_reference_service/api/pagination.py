"""Parámetros HTTP compartidos para paginación."""

from typing import Annotated

from fastapi import Query

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


class PaginationParams:
    """Representa los parámetros HTTP de paginación.

    Attributes:
        page: Número de página solicitado, iniciando en uno.
        page_size: Cantidad máxima de registros por página.
    """

    def __init__(
        self,
        page: Annotated[
            int,
            Query(
                ge=1,
                description="Número de página solicitado.",
            ),
        ] = DEFAULT_PAGE,
        page_size: Annotated[
            int,
            Query(
                ge=1,
                le=MAX_PAGE_SIZE,
                description="Cantidad de registros por página.",
            ),
        ] = DEFAULT_PAGE_SIZE,
    ) -> None:
        """Inicializa los parámetros de paginación.

        Args:
            page: Número de página solicitado.
            page_size: Cantidad máxima de registros por página.
        """
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        """Calcula el desplazamiento correspondiente a la página.

        Returns:
            Cantidad de registros que deben omitirse.
        """
        return (self.page - 1) * self.page_size