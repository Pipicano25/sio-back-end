"""Filtros HTTP para métodos globales de pago."""

from typing import Annotated

from fastapi import Query

from payment_reference_service.domain.global_payment_methods import (
    PaymentMethodStatus,
    PaymentMethodType,
)


class GlobalPaymentMethodFilters:
    """Agrupa los filtros disponibles para métodos globales de pago."""

    def __init__(
        self,
        search: Annotated[
            str | None,
            Query(
                description="Busca por código o nombre.",
            ),
        ] = None,
        status: Annotated[
            PaymentMethodStatus | None,
            Query(
                description="Filtra por estado exacto.",
            ),
        ] = None,
        method_type: Annotated[
            PaymentMethodType | None,
            Query(
                description="Filtra por tipo funcional exacto.",
            ),
        ] = None,
        requires_reference: Annotated[
            bool | None,
            Query(
                description=(
                    "Filtra según si el método requiere referencia externa."
                ),
            ),
        ] = None,
    ) -> None:
        """Inicializa los filtros HTTP.

        Args:
            search: Texto general de búsqueda.
            status: Estado exacto opcional.
            method_type: Tipo funcional opcional.
            requires_reference: Filtro booleano opcional.
        """
        self.search = search
        self.status = status
        self.method_type = method_type
        self.requires_reference = requires_reference
