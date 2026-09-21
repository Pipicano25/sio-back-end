"""Filtros HTTP para condiciones globales de pago."""

from typing import Annotated

from fastapi import Query

from payment_reference_service.domain.global_payment_condition_types import (
    PaymentConditionStatus,
)


class GlobalPaymentConditionTypeFilters:
    """Agrupa los filtros HTTP disponibles para el recurso."""

    def __init__(
        self,
        search: Annotated[
            str | None,
            Query(
                description=(
                    "Busca por código, nombre o descripción."
                )
            ),
        ] = None,
        status: Annotated[
            PaymentConditionStatus | None,
            Query(
                description="Filtra por estado exacto."
            ),
        ] = None,
    ) -> None:
        """Inicializa los filtros.

        Args:
            search: Texto general de búsqueda.
            status: Estado exacto opcional.
        """
        self.search = search
        self.status = status