"""Utilidades HTTP compartidas para paginación."""

from fastapi import Query


class PaginationParams:
    """Representa los parámetros de paginación recibidos por la API."""

    def __init__(
        self,
        page: int = Query(
            default=1,
            ge=1,
            description="Número de página solicitado.",
        ),
        page_size: int = Query(
            default=20,
            ge=1,
            le=100,
            description="Cantidad de registros por página.",
        ),
    ) -> None:
        """Inicializa los parámetros de paginación.

        Args:
            page: Número de página solicitado.
            page_size: Cantidad máxima de registros por página.
        """
        self.page = page
        self.page_size = page_size
