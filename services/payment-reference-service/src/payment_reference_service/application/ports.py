"""Contratos de persistencia de Payment Reference Service."""

from typing import Protocol
from uuid import UUID

from payment_reference_service.application.pagination import PageResult
from payment_reference_service.domain.global_payment_condition_types import (
    GlobalPaymentConditionType,
    PaymentConditionStatus,
)
from payment_reference_service.domain.global_payment_methods import (
    GlobalPaymentMethod,
    PaymentMethodStatus,
    PaymentMethodType,
)


class GlobalPaymentConditionTypeRepository(Protocol):
    """Contrato de persistencia para condiciones globales de pago."""

    def get_by_id(
        self,
        condition_type_id: UUID,
    ) -> GlobalPaymentConditionType | None:
        """Obtiene una condición mediante su identificador.

        Args:
            condition_type_id: Identificador del registro.

        Returns:
            Registro encontrado o `None`.
        """
        ...

    def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: PaymentConditionStatus | None,
    ) -> PageResult[GlobalPaymentConditionType]:
        """Obtiene condiciones utilizando búsqueda, filtros y paginación.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros por página.
            search: Texto general de búsqueda.
            status: Estado exacto opcional.

        Returns:
            Resultado paginado.
        """
        ...

    def create(
        self,
        entity: GlobalPaymentConditionType,
    ) -> GlobalPaymentConditionType:
        """Persiste una nueva condición.

        Args:
            entity: Entidad que debe almacenarse.

        Returns:
            Entidad persistida.
        """
        ...

    def update(
        self,
        entity: GlobalPaymentConditionType,
    ) -> GlobalPaymentConditionType:
        """Persiste los cambios de una condición existente.

        Args:
            entity: Estado completo actualizado.

        Returns:
            Entidad actualizada.
        """
        ...

    def delete(self, condition_type_id: UUID) -> None:
        """Elimina físicamente una condición.

        Args:
            condition_type_id: Identificador del registro.
        """
        ...


class GlobalPaymentMethodRepository(Protocol):
    """Contrato de persistencia para métodos globales de pago."""

    def get_by_id(
        self,
        payment_method_id: UUID,
    ) -> GlobalPaymentMethod | None:
        """Obtiene un método de pago mediante su identificador.

        Args:
            payment_method_id: Identificador del registro.

        Returns:
            Método encontrado o `None`.
        """
        ...

    def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: PaymentMethodStatus | None,
        method_type: PaymentMethodType | None,
        requires_reference: bool | None,
    ) -> PageResult[GlobalPaymentMethod]:
        """Lista métodos de pago utilizando búsqueda y filtros.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros por página.
            search: Texto general de búsqueda.
            status: Estado exacto opcional.
            method_type: Tipo funcional opcional.
            requires_reference: Filtro opcional de referencia requerida.

        Returns:
            Resultado paginado.
        """
        ...

    def create(
        self,
        entity: GlobalPaymentMethod,
    ) -> GlobalPaymentMethod:
        """Persiste un nuevo método de pago.

        Args:
            entity: Entidad que debe persistirse.

        Returns:
            Entidad persistida.
        """
        ...

    def update(
        self,
        entity: GlobalPaymentMethod,
    ) -> GlobalPaymentMethod:
        """Persiste la actualización completa de un método.

        Args:
            entity: Estado completo actualizado.

        Returns:
            Entidad persistida.
        """
        ...

    def delete(self, payment_method_id: UUID) -> None:
        """Elimina físicamente un método de pago.

        Args:
            payment_method_id: Identificador del registro.
        """
        ...
