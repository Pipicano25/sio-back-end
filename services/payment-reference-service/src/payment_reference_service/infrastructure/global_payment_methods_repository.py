"""Repositorio SQLAlchemy para métodos globales de pago."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from payment_reference_service.application.exceptions import (
    GlobalPaymentMethodConflictError,
    GlobalPaymentMethodNotFoundError,
)
from payment_reference_service.application.pagination import PageResult
from payment_reference_service.domain.global_payment_methods import (
    GlobalPaymentMethod,
    PaymentMethodStatus,
    PaymentMethodType,
)
from payment_reference_service.infrastructure.models import (
    GlobalPaymentMethodModel,
)


class SqlAlchemyGlobalPaymentMethodRepository:
    """Implementa persistencia de métodos globales mediante SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        """Inicializa el repositorio.

        Args:
            session: Sesión SQLAlchemy activa.
        """
        self._session = session

    def get_by_id(
        self,
        payment_method_id: UUID,
    ) -> GlobalPaymentMethod | None:
        """Obtiene un método mediante su identificador.

        Args:
            payment_method_id: Identificador del registro.

        Returns:
            Entidad encontrada o `None`.
        """
        model = self._session.get(
            GlobalPaymentMethodModel,
            payment_method_id,
        )

        if model is None:
            return None

        return self._to_domain(model)

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
        """Obtiene métodos utilizando búsqueda, filtros y paginación.

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
        conditions = []

        if search:
            pattern = f"%{search}%"

            conditions.append(
                or_(
                    GlobalPaymentMethodModel.code.ilike(pattern),
                    GlobalPaymentMethodModel.name.ilike(pattern),
                )
            )

        if status is not None:
            conditions.append(
                GlobalPaymentMethodModel.status == status.value
            )

        if method_type is not None:
            conditions.append(
                GlobalPaymentMethodModel.method_type == method_type.value
            )

        if requires_reference is not None:
            conditions.append(
                GlobalPaymentMethodModel.requires_reference
                == requires_reference
            )

        count_statement = (
            select(func.count())
            .select_from(GlobalPaymentMethodModel)
            .where(*conditions)
        )

        total_records = self._session.scalar(count_statement) or 0

        statement = (
            select(GlobalPaymentMethodModel)
            .where(*conditions)
            .order_by(
                GlobalPaymentMethodModel.code.asc(),
                GlobalPaymentMethodModel.id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        models = self._session.scalars(statement).all()

        return PageResult(
            items=[self._to_domain(model) for model in models],
            page=page,
            page_size=page_size,
            total_records=total_records,
        )

    def create(
        self,
        entity: GlobalPaymentMethod,
    ) -> GlobalPaymentMethod:
        """Persiste un nuevo método de pago.

        Args:
            entity: Entidad que debe persistirse.

        Returns:
            Entidad persistida.

        Raises:
            GlobalPaymentMethodConflictError: Si existe un conflicto de
                integridad.
        """
        model = self._from_domain(entity)

        self._session.add(model)

        try:
            self._session.commit()
            self._session.refresh(model)
        except IntegrityError as exc:
            self._session.rollback()

            raise GlobalPaymentMethodConflictError(
                "Ya existe un método de pago con el código indicado."
            ) from exc

        return self._to_domain(model)

    def update(
        self,
        entity: GlobalPaymentMethod,
    ) -> GlobalPaymentMethod:
        """Persiste la actualización completa de un método de pago.

        Args:
            entity: Entidad actualizada.

        Returns:
            Entidad persistida.

        Raises:
            GlobalPaymentMethodNotFoundError: Si el registro no existe.
            GlobalPaymentMethodConflictError: Si existe conflicto de
                integridad.
        """
        model = self._session.get(
            GlobalPaymentMethodModel,
            entity.id,
        )

        if model is None:
            raise GlobalPaymentMethodNotFoundError(
                "El método de pago solicitado no existe."
            )

        model.code = entity.code
        model.name = entity.name
        model.method_type = entity.method_type.value
        model.requires_reference = entity.requires_reference
        model.status = entity.status.value
        model.updated_by = entity.updated_by
        model.updated_at = entity.updated_at

        try:
            self._session.commit()
            self._session.refresh(model)
        except IntegrityError as exc:
            self._session.rollback()

            raise GlobalPaymentMethodConflictError(
                "Ya existe un método de pago con el código indicado."
            ) from exc

        return self._to_domain(model)

    @staticmethod
    def _to_domain(
        model: GlobalPaymentMethodModel,
    ) -> GlobalPaymentMethod:
        """Convierte un modelo SQLAlchemy en entidad de dominio.

        Args:
            model: Modelo persistente.

        Returns:
            Entidad de dominio.
        """
        return GlobalPaymentMethod(
            id=model.id,
            code=model.code,
            name=model.name,
            method_type=PaymentMethodType(model.method_type),
            requires_reference=model.requires_reference,
            status=PaymentMethodStatus(model.status),
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _from_domain(
        entity: GlobalPaymentMethod,
    ) -> GlobalPaymentMethodModel:
        """Convierte una entidad de dominio en modelo SQLAlchemy.

        Args:
            entity: Entidad de dominio.

        Returns:
            Modelo preparado para persistencia.
        """
        return GlobalPaymentMethodModel(
            id=entity.id,
            code=entity.code,
            name=entity.name,
            method_type=entity.method_type.value,
            requires_reference=entity.requires_reference,
            status=entity.status.value,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
