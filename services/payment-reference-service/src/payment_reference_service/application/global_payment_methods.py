"""Casos de uso de métodos globales de pago."""

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

from payment_reference_service.application.exceptions import (
    GlobalPaymentMethodNotFoundError,
)
from payment_reference_service.application.pagination import PageResult
from payment_reference_service.application.ports import (
    GlobalPaymentMethodRepository,
)
from payment_reference_service.domain.global_payment_methods import (
    GlobalPaymentMethod,
    PaymentMethodStatus,
    PaymentMethodType,
)


class GlobalPaymentMethodService:
    """Implementa los casos de uso de métodos globales de pago."""

    def __init__(
        self,
        repository: GlobalPaymentMethodRepository,
    ) -> None:
        """Inicializa el servicio de aplicación.

        Args:
            repository: Repositorio utilizado para persistencia.
        """
        self._repository = repository

    def get_by_id(
        self,
        payment_method_id: UUID,
    ) -> GlobalPaymentMethod:
        """Obtiene un método mediante su identificador.

        Args:
            payment_method_id: Identificador del registro.

        Returns:
            Método encontrado.

        Raises:
            GlobalPaymentMethodNotFoundError: Si el registro no existe.
        """
        entity = self._repository.get_by_id(payment_method_id)

        if entity is None:
            raise GlobalPaymentMethodNotFoundError(
                "El método de pago solicitado no existe."
            )

        return entity

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
        """Lista métodos utilizando búsqueda, filtros y paginación.

        Args:
            page: Página solicitada.
            page_size: Cantidad máxima de registros por página.
            search: Texto general de búsqueda.
            status: Estado exacto opcional.
            method_type: Tipo funcional opcional.
            requires_reference: Filtro opcional por referencia requerida.

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
            method_type=method_type,
            requires_reference=requires_reference,
        )

    def create(
        self,
        *,
        code: str,
        name: str,
        method_type: PaymentMethodType,
        requires_reference: bool,
        status: PaymentMethodStatus,
        actor_id: str,
    ) -> GlobalPaymentMethod:
        """Crea un método global de pago.

        Args:
            code: Código estable del método.
            name: Nombre visible.
            method_type: Clasificación funcional.
            requires_reference: Indica si requiere referencia externa.
            status: Estado inicial.
            actor_id: Subject OIDC del usuario autenticado.

        Returns:
            Entidad creada.
        """
        now = datetime.now(timezone.utc)

        entity = GlobalPaymentMethod(
            id=uuid4(),
            code=code,
            name=name,
            method_type=method_type,
            requires_reference=requires_reference,
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
        payment_method_id: UUID,
        code: str,
        name: str,
        method_type: PaymentMethodType,
        requires_reference: bool,
        status: PaymentMethodStatus,
        actor_id: str,
    ) -> GlobalPaymentMethod:
        """Actualiza completamente un método global de pago.

        Args:
            payment_method_id: Identificador del registro.
            code: Código estable.
            name: Nombre visible.
            method_type: Clasificación funcional.
            requires_reference: Indica si requiere referencia externa.
            status: Estado actualizado.
            actor_id: Subject OIDC del usuario autenticado.

        Returns:
            Entidad actualizada.

        Raises:
            GlobalPaymentMethodNotFoundError: Si el registro no existe.
        """
        current = self.get_by_id(payment_method_id)

        updated = replace(
            current,
            code=code,
            name=name,
            method_type=method_type,
            requires_reference=requires_reference,
            status=status,
            updated_by=actor_id,
            updated_at=datetime.now(timezone.utc),
        )

        return self._repository.update(updated)

    def delete(self, payment_method_id: UUID) -> None:
        """Elimina físicamente un método global de pago.

        Args:
            payment_method_id: Identificador del registro.

        Raises:
            GlobalPaymentMethodNotFoundError: Si el registro no existe.
        """
        self.get_by_id(payment_method_id)
        self._repository.delete(payment_method_id)
