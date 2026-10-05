"""Casos de uso de tipos globales de condición de pago.

Feature 008: sin borrado físico (D7); el estado solo cambia con las acciones
explícitas `deactivate` y `reactivate`; toda escritura exige la versión que el
cliente leyó (Principio VII). Orden de comprobación: existencia → versión →
transición.
"""

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from payment_reference_service.application.exceptions import (
    VERSION_CONFLICT_MESSAGE,
    GlobalPaymentConditionTypeNotFoundError,
    GlobalPaymentConditionTypeVersionConflictError,
)
from payment_reference_service.application.pagination import PageResult
from payment_reference_service.application.ports import (
    GlobalPaymentConditionTypeRepository,
)
from payment_reference_service.domain.global_payment_condition_types import (
    GlobalPaymentConditionType,
    PaymentConditionStatus,
    deactivated_status,
    reactivated_status,
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
        actor_id: str,
    ) -> GlobalPaymentConditionType:
        """Crea un tipo global de condición de pago, siempre `ACTIVE` (FR-017).

        Args:
            code: Código estable del registro.
            name: Nombre visible.
            description: Descripción opcional.
            actor_id: Subject OIDC del usuario autenticado.

        Returns:
            Entidad creada, con versión 1.
        """
        now = datetime.now(timezone.utc)

        entity = GlobalPaymentConditionType(
            id=uuid4(),
            code=code,
            name=name,
            description=description,
            status=PaymentConditionStatus.ACTIVE,
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
        version: int,
        code: str,
        name: str,
        description: str | None,
        actor_id: str,
    ) -> GlobalPaymentConditionType:
        """Reemplaza los campos modificables sin cambiar el estado (FR-016, FR-016a).

        Args:
            condition_type_id: Identificador del registro.
            version: Versión que el cliente leyó.
            code: Código estable.
            name: Nombre visible.
            description: Descripción opcional (nula si se omite).
            actor_id: Subject OIDC del usuario autenticado.

        Returns:
            Entidad actualizada.

        Raises:
            GlobalPaymentConditionTypeNotFoundError: Si no existe.
            GlobalPaymentConditionTypeVersionConflictError: Si la versión no
                coincide.
        """
        current = self._current(condition_type_id, version)

        updated = replace(
            current,
            code=code,
            name=name,
            description=description,
            updated_by=actor_id,
            updated_at=datetime.now(timezone.utc),
        )

        return self._repository.update(updated, expected_version=version)

    def deactivate(
        self,
        condition_type_id: UUID,
        *,
        version: int,
        actor_id: str,
    ) -> GlobalPaymentConditionType:
        """Inactiva un tipo `ACTIVE` sin borrarlo (FR-012).

        Raises:
            GlobalPaymentConditionTypeNotFoundError: Si no existe.
            GlobalPaymentConditionTypeVersionConflictError: Si la versión no
                coincide.
            InvalidStatusTransitionError: Si ya está inactivo.
        """
        current = self._current(condition_type_id, version)
        return self._change_status(current, deactivated_status(current.status), version, actor_id)

    def reactivate(
        self,
        condition_type_id: UUID,
        *,
        version: int,
        actor_id: str,
    ) -> GlobalPaymentConditionType:
        """Reactiva un tipo `INACTIVE` (FR-013).

        Raises:
            GlobalPaymentConditionTypeNotFoundError: Si no existe.
            GlobalPaymentConditionTypeVersionConflictError: Si la versión no
                coincide.
            InvalidStatusTransitionError: Si ya está activo.
        """
        current = self._current(condition_type_id, version)
        return self._change_status(current, reactivated_status(current.status), version, actor_id)

    def _current(self, condition_type_id: UUID, version: int) -> GlobalPaymentConditionType:
        """Existencia y versión, en ese orden, antes de cualquier regla de estado."""
        current = self.get_by_id(condition_type_id)

        if current.version != version:
            raise GlobalPaymentConditionTypeVersionConflictError(VERSION_CONFLICT_MESSAGE)

        return current

    def _change_status(
        self,
        current: GlobalPaymentConditionType,
        status: PaymentConditionStatus,
        version: int,
        actor_id: str,
    ) -> GlobalPaymentConditionType:
        updated = replace(
            current,
            status=status,
            updated_by=actor_id,
            updated_at=datetime.now(timezone.utc),
        )

        return self._repository.update(updated, expected_version=version)
