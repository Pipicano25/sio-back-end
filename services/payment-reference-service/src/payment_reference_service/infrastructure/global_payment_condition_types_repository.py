"""Repositorio SQLAlchemy para condiciones globales de pago."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from payment_reference_service.application.exceptions import (
    GlobalPaymentConditionTypeConflictError,
    GlobalPaymentConditionTypeNotFoundError,
    GlobalPaymentConditionTypeVersionConflictError,
    VERSION_CONFLICT_MESSAGE,
)
from payment_reference_service.application.pagination import PageResult
from payment_reference_service.domain.global_payment_condition_types import (
    GlobalPaymentConditionType,
    PaymentConditionStatus,
)
from payment_reference_service.infrastructure.models import (
    GlobalPaymentConditionTypeModel,
)


class SqlAlchemyGlobalPaymentConditionTypeRepository:
    """Implementa persistencia de condiciones usando SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        """Inicializa el repositorio.

        Args:
            session: Sesión SQLAlchemy activa.
        """
        self._session = session

    def get_by_id(
        self,
        condition_type_id: UUID,
    ) -> GlobalPaymentConditionType | None:
        """Obtiene una condición mediante su identificador.

        Args:
            condition_type_id: Identificador del registro.

        Returns:
            Entidad encontrada o `None`.
        """
        model = self._session.get(
            GlobalPaymentConditionTypeModel,
            condition_type_id,
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
        status: PaymentConditionStatus | None,
    ) -> PageResult[GlobalPaymentConditionType]:
        """Obtiene una página utilizando búsqueda y filtros.

        Args:
            page: Página solicitada.
            page_size: Registros máximos por página.
            search: Texto general de búsqueda.
            status: Estado exacto opcional.

        Returns:
            Resultado paginado.
        """
        conditions = []

        if search:
            pattern = f"%{search}%"

            conditions.append(
                or_(
                    GlobalPaymentConditionTypeModel.code.ilike(pattern),
                    GlobalPaymentConditionTypeModel.name.ilike(pattern),
                    GlobalPaymentConditionTypeModel.description.ilike(pattern),
                )
            )

        if status is not None:
            conditions.append(
                GlobalPaymentConditionTypeModel.status == status.value
            )

        count_statement = (
            select(func.count())
            .select_from(GlobalPaymentConditionTypeModel)
            .where(*conditions)
        )

        total_records = self._session.scalar(count_statement) or 0

        statement = (
            select(GlobalPaymentConditionTypeModel)
            .where(*conditions)
            .order_by(
                GlobalPaymentConditionTypeModel.code.asc(),
                GlobalPaymentConditionTypeModel.id.asc(),
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
        entity: GlobalPaymentConditionType,
    ) -> GlobalPaymentConditionType:
        """Persiste una nueva condición.

        Args:
            entity: Entidad que debe persistirse.

        Returns:
            Entidad persistida.

        Raises:
            GlobalPaymentConditionTypeConflictError: Si existe conflicto
                de integridad.
        """
        model = self._from_domain(entity)

        self._session.add(model)

        try:
            self._session.commit()
            self._session.refresh(model)
        except IntegrityError as exc:
            self._session.rollback()

            raise GlobalPaymentConditionTypeConflictError(
                "Ya existe un tipo de condición de pago con el código indicado."
            ) from exc

        return self._to_domain(model)

    def update(
        self,
        entity: GlobalPaymentConditionType,
        *,
        expected_version: int,
    ) -> GlobalPaymentConditionType:
        """Persiste la actualización completa con concurrencia optimista.

        La fila vigente debe tener `expected_version`; el `UPDATE … WHERE
        version = :vigente` que genera `version_id_col` resuelve además la
        carrera entre dos solicitudes que leyeron la misma versión.

        Args:
            entity: Entidad actualizada.
            expected_version: Versión que el cliente leyó.

        Returns:
            Entidad persistida, con la versión incrementada.

        Raises:
            GlobalPaymentConditionTypeNotFoundError: Si no existe.
            GlobalPaymentConditionTypeVersionConflictError: Si la versión no
                coincide o la fila cambió entre la lectura y la escritura.
            GlobalPaymentConditionTypeConflictError: Si existe conflicto
                de integridad (código duplicado).
        """
        model = self._session.get(
            GlobalPaymentConditionTypeModel,
            entity.id,
        )

        if model is None:
            raise GlobalPaymentConditionTypeNotFoundError(
                "El tipo de condición de pago solicitado no existe."
            )

        if model.version != expected_version:
            raise GlobalPaymentConditionTypeVersionConflictError(VERSION_CONFLICT_MESSAGE)

        model.code = entity.code
        model.name = entity.name
        model.description = entity.description
        model.status = entity.status.value
        model.updated_by = entity.updated_by
        model.updated_at = entity.updated_at

        try:
            self._session.commit()
            self._session.refresh(model)
        except StaleDataError as exc:
            self._session.rollback()

            raise GlobalPaymentConditionTypeVersionConflictError(
                VERSION_CONFLICT_MESSAGE
            ) from exc
        except IntegrityError as exc:
            self._session.rollback()

            raise GlobalPaymentConditionTypeConflictError(
                "Ya existe un tipo de condición de pago con el código indicado."
            ) from exc

        return self._to_domain(model)

    @staticmethod
    def _to_domain(
        model: GlobalPaymentConditionTypeModel,
    ) -> GlobalPaymentConditionType:
        """Convierte un modelo SQLAlchemy en entidad de dominio.

        Args:
            model: Modelo persistente.

        Returns:
            Entidad de dominio.
        """
        return GlobalPaymentConditionType(
            id=model.id,
            code=model.code,
            name=model.name,
            description=model.description,
            status=PaymentConditionStatus(model.status),
            created_by=model.created_by,
            updated_by=model.updated_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

    @staticmethod
    def _from_domain(
        entity: GlobalPaymentConditionType,
    ) -> GlobalPaymentConditionTypeModel:
        """Convierte una entidad de dominio en modelo SQLAlchemy.

        Args:
            entity: Entidad de dominio.

        Returns:
            Modelo preparado para persistencia.
        """
        return GlobalPaymentConditionTypeModel(
            id=entity.id,
            code=entity.code,
            name=entity.name,
            description=entity.description,
            status=entity.status.value,
            created_by=entity.created_by,
            updated_by=entity.updated_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )