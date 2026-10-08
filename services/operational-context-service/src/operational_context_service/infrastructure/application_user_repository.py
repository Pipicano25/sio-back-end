"""Repositorio SQLAlchemy de usuarios operativos (membresías, Fase B).

Las lecturas hacen `JOIN` con `companies` para devolver `company_status`
(calculado, no persistido). El alta y la reactivación leen la empresa con
`SELECT ... FOR SHARE` dentro de la transacción de escritura: nunca queda una
membresía creada o reactivada bajo una empresa inactiva (RN-10). La unicidad de
membresía `ACTIVE` la garantizan índices únicos parciales (R-04).
"""

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from operational_context_service.application import audit_events as audit
from operational_context_service.application.exceptions import (
    CompanyInactiveError,
    DuplicateMembershipError,
    InvalidStatusTransitionError,
    NotFoundError,
)
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.ports import ApplicationUserFilters
from operational_context_service.domain.entities import ApplicationUser
from operational_context_service.infrastructure.models import ApplicationUserModel, CompanyModel
from operational_context_service.infrastructure.persistence import (
    commit_or_translate,
    load_for_update,
)

UNIQUE_PERSON = "uq_application_users_company_id_person_identity_id_active"
UNIQUE_SUB = "uq_application_users_company_id_keycloak_user_id_active"
NOT_FOUND_MESSAGE = "El usuario operativo solicitado no existe."
COMPANY_NOT_FOUND_MESSAGE = "La empresa solicitada no existe."


def _user_query() -> Select:
    return select(
        ApplicationUserModel,
        CompanyModel.status.label("company_status"),
    ).join(CompanyModel, CompanyModel.id == ApplicationUserModel.company_id)


class SQLAlchemyApplicationUserRepository:
    """Persistencia de membresías."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def end_read(self) -> None:
        """Cierra la transacción de lectura antes de llamar a otros servicios (R-09 de la Fase A)."""
        if self.session.in_transaction():
            self.session.rollback()

    def get_by_id(self, application_user_id: UUID) -> ApplicationUser | None:
        row = self.session.execute(
            _user_query()
            .where(ApplicationUserModel.id == application_user_id)
            .execution_options(populate_existing=True)
        ).one_or_none()

        return None if row is None else to_application_user(*row)

    def list_by_subject(self, keycloak_user_id: str) -> list[ApplicationUser]:
        """Todas las membresías (activas e inactivas) de un `sub`, más antiguas primero."""
        rows = self.session.execute(
            _user_query()
            .where(ApplicationUserModel.keycloak_user_id == keycloak_user_id)
            .order_by(ApplicationUserModel.created_at, ApplicationUserModel.id)
        ).all()

        return [to_application_user(*row) for row in rows]

    def exists_active(
        self,
        company_id: UUID,
        *,
        person_identity_id: UUID | None = None,
        keycloak_user_id: str | None = None,
        exclude_id: UUID | None = None,
    ) -> bool:
        statement = select(ApplicationUserModel.id).where(
            ApplicationUserModel.company_id == company_id,
            ApplicationUserModel.status == "ACTIVE",
        )

        if person_identity_id is not None:
            statement = statement.where(ApplicationUserModel.person_identity_id == person_identity_id)

        if keycloak_user_id is not None:
            statement = statement.where(ApplicationUserModel.keycloak_user_id == keycloak_user_id)

        if exclude_id is not None:
            statement = statement.where(ApplicationUserModel.id != exclude_id)

        return self.session.scalar(statement.limit(1)) is not None

    def list_by_company(
        self,
        company_id: UUID,
        filters: ApplicationUserFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[ApplicationUser]:
        conditions = [
            ApplicationUserModel.company_id == company_id,
            ApplicationUserModel.status == filters.status,
        ]

        if filters.keycloak_user_id is not None:
            conditions.append(ApplicationUserModel.keycloak_user_id == filters.keycloak_user_id)

        if filters.person_identity_id is not None:
            conditions.append(ApplicationUserModel.person_identity_id == filters.person_identity_id)

        if filters.search:
            pattern = f"%{filters.search}%"
            conditions.append(
                or_(
                    ApplicationUserModel.display_name.ilike(pattern),
                    ApplicationUserModel.reference_email.ilike(pattern),
                )
            )

        total_records = self.session.scalar(
            select(func.count()).select_from(ApplicationUserModel).where(*conditions)
        ) or 0

        rows = self.session.execute(
            _user_query()
            .where(*conditions)
            .order_by(ApplicationUserModel.created_at, ApplicationUserModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return PageResult(
            items=[to_application_user(*row) for row in rows],
            page=page,
            page_size=page_size,
            total_records=total_records,
        )

    def create_in_active_company(
        self,
        company_id: UUID,
        values: dict[str, Any],
        *,
        actor_id: str,
    ) -> ApplicationUser:
        """Inserta la membresía si la empresa sigue `ACTIVE` (bloqueo `FOR SHARE`)."""
        self._lock_active_company(company_id)
        application_user_id = uuid4()
        model = ApplicationUserModel(
            id=application_user_id,
            company_id=company_id,
            **values,
            status="ACTIVE",
            created_by=actor_id,
            updated_by=actor_id,
        )
        self.session.add(model)
        audit.track_create(
            self.session, model, action=audit.CREATE_APPLICATION_USER, entity_type="ApplicationUser",
            company_id=company_id,
        )
        self._commit()

        return self._reload(application_user_id)

    def update(
        self,
        application_user_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> ApplicationUser:
        model = load_for_update(
            self.session,
            ApplicationUserModel,
            application_user_id,
            expected_version=expected_version,
            not_found_message=NOT_FOUND_MESSAGE,
        )

        for field, value in values.items():
            setattr(model, field, value)

        model.updated_by = actor_id
        audit.track_update(
            self.session, model, action=audit.status_action(model, "APPLICATION_USER"),
            entity_type="ApplicationUser", company_id=model.company_id,
        )
        self._commit()

        return self._reload(application_user_id)

    def reactivate_in_active_company(
        self,
        application_user_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> ApplicationUser:
        """Reactiva si la empresa sigue `ACTIVE`; el índice parcial impide dos `ACTIVE`."""
        model = load_for_update(
            self.session,
            ApplicationUserModel,
            application_user_id,
            expected_version=expected_version,
            not_found_message=NOT_FOUND_MESSAGE,
        )

        if model.status == "ACTIVE":
            self.session.rollback()
            raise InvalidStatusTransitionError("El usuario operativo ya se encuentra en estado ACTIVE.")

        self._lock_active_company(model.company_id)
        model.status = "ACTIVE"
        model.updated_by = actor_id
        audit.track_update(
            self.session, model, action=audit.REACTIVATE_APPLICATION_USER, entity_type="ApplicationUser",
            company_id=model.company_id,
        )
        self._commit()

        return self._reload(application_user_id)

    def _lock_active_company(self, company_id: UUID) -> None:
        status = self.session.execute(
            select(CompanyModel.status)
            .where(CompanyModel.id == company_id)
            .with_for_update(read=True)
        ).scalar_one_or_none()

        if status is None:
            self.session.rollback()
            raise NotFoundError(COMPANY_NOT_FOUND_MESSAGE)

        if status != "ACTIVE":
            self.session.rollback()
            raise CompanyInactiveError(
                "La empresa está inactiva: no se pueden registrar ni reactivar sus usuarios operativos."
            )

    def _commit(self) -> None:
        commit_or_translate(
            self.session,
            duplicates={
                UNIQUE_PERSON: DuplicateMembershipError(
                    "Ya existe una membresía activa de esa persona en la empresa.",
                    field="person_identity_id",
                ),
                UNIQUE_SUB: DuplicateMembershipError(
                    "Ya existe una membresía activa de esa cuenta en la empresa.",
                    field="keycloak_user_id",
                ),
            },
        )

    def _reload(self, application_user_id: UUID) -> ApplicationUser:
        user = self.get_by_id(application_user_id)
        self.end_read()

        if user is None:  # pragma: no cover - la fila acaba de confirmarse
            raise NotFoundError(NOT_FOUND_MESSAGE)

        return user


def to_application_user(model: ApplicationUserModel, company_status: str) -> ApplicationUser:
    """Convierte la fila (modelo + estado de la empresa) en entidad de dominio."""
    return ApplicationUser(
        id=model.id,
        company_id=model.company_id,
        company_status=company_status,
        keycloak_user_id=model.keycloak_user_id,
        person_identity_id=model.person_identity_id,
        display_name=model.display_name,
        reference_email=model.reference_email,
        status=model.status,
        version=model.version,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
