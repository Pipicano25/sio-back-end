"""Casos de uso de tipos globales de condición de pago."""

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from payment_reference_service.application.exceptions import (
    GlobalPaymentConditionTypeNotFoundError,
)
from payment_reference_service.application.pagination import PageResult
from payment_reference_service.application.ports import (
    GlobalPaymentConditionTypeRepository,
)
from payment_reference_service.domain.global_payment_condition_types import (
    GlobalPaymentConditionType,
    PaymentConditionStatus,
)


class GlobalPaymentConditionTypeService:
    """Implementa los casos de uso de condiciones globales de pago."""

    def __init__(
        self,
        repository: GlobalPaymentConditionTypeRepository,
    ) -> None:
        """Inicializa el servicio de aplicación.

        Args:
            repository: Repositorio utilizado para persistencia.
        """
        self._repository = repository

    def get_by_id(
        self,
        condition_type_id: UUID,
    ) -> GlobalPaymentConditionType:
        """Obtiene una condición mediante su identificador.

        Args:
            condition_type_id: Identificador del registro.

        Returns:
            Condición encontrada.

        Raises:
            GlobalPaymentConditionTypeNotFoundError: Si no existe.
        """
        entity = self._repository.get_by_id(condition_type_id)

        if entity is None:
            raise GlobalPaymentConditionTypeNotFoundError(
                "El tipo de condición de pago solicitado no existe."
            )

        return entity

    def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        status: PaymentConditionStatus | None,
    ) -> PageResult[GlobalPaymentConditionType]:
        """Lista condiciones con búsqueda, filtros y paginación.

        Args:
            page: Página solicitada.
            page_size: Cantidad de registros por página.
            search: Texto general de búsqueda.
            status: Estado exacto opcional.

        Returns:
            Resultado paginado.
        """
        normalized_search = search.strip() if search else None

        if not normalized_search:
            normalized_search = None

        return self._repository.list(
            page=page,
            page_size=page_size,
            search=normalized_search,
            status=status,
        )

    def create(
        self,
        *,
        code: str,
        name: str,
        description: str | None,
        status: PaymentConditionStatus,
        actor_id: str,
    ) -> GlobalPaymentConditionType:
        """Crea un tipo global de condición de pago.

        Args:
            code: Código estable del registro.
            name: Nombre visible.
            description: Descripción opcional.
            status: Estado inicial.
            actor_id: Subject OIDC del usuario autenticado.

        Returns:
            Entidad creada.
        """
        now = datetime.now(timezone.utc)

        entity = GlobalPaymentConditionType(
            id=uuid4(),
            code=code,
            name=name,
            description=description,
            status=status,
            created_by=actor_id,
            updated_by=actor_id,
            created_at=now,
            updated_at=now,
        )

        return self._repository.create(entity)

    def update(
        self,
        *,
        condition_type_id: UUID,
        code: str,
        name: str,
        description: str | None,
        status: PaymentConditionStatus,
        actor_id: str,
    ) -> GlobalPaymentConditionType:
        """Actualiza completamente una condición existente.

        Args:
            condition_type_id: Identificador del registro.
            code: Código estable.
            name: Nombre visible.
            description: Descripción opcional.
            status: Estado actualizado.
            actor_id: Subject OIDC del usuario autenticado.

        Returns:
            Entidad actualizada.

        Raises:
            GlobalPaymentConditionTypeNotFoundError: Si no existe.
        """
        current = self.get_by_id(condition_type_id)

        updated = replace(
            current,
            code=code,
            name=name,
            description=description,
            status=status,
            updated_by=actor_id,
            updated_at=datetime.now(timezone.utc),
        )

        return self._repository.update(updated)

    def delete(self, condition_type_id: UUID) -> None:
        """Elimina físicamente una condición.

        Args:
            condition_type_id: Identificador del registro.

        Raises:
            GlobalPaymentConditionTypeNotFoundError: Si no existe.
        """
        self.get_by_id(condition_type_id)
        self._repository.delete(condition_type_id)