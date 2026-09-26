"""Repositorio SQLAlchemy de asignaciones de asesor (Fase B, DS-13).

Una asignación cerrada es inmutable. El cambio de asesor principal cierra la
vigente y crea la nueva en **una sola transacción** con `SELECT ... FOR UPDATE`
sobre la vigente (R-12): o se aplican ambas escrituras o ninguna. Los índices
únicos parciales impiden dos principales vigentes o la misma persona vigente
dos veces en una empresa, también bajo concurrencia.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from operational_context_service.application.exceptions import (
    CompanyInactiveError,
    DuplicateAdvisorAssignmentError,
    InvalidStatusTransitionError,
    NotFoundError,
    PrimaryAdvisorExistsError,
    PrimaryAdvisorMismatchError,
    VersionConflictError,
)
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.ports import AdvisorFilters
from operational_context_service.domain.entities import AdvisorAssignment
from operational_context_service.domain.validity import InvalidValidityPeriodError
from operational_context_service.infrastructure.models import (
    CompanyAdvisorAssignmentModel,
    CompanyModel,
)
from operational_context_service.infrastructure.persistence import (
    commit_or_translate,
    load_for_update,
)

UNIQUE_PRIMARY = "uq_company_advisor_assignments_company_id_primary_active"
UNIQUE_PERSON = "uq_company_advisor_assignments_company_person_active"
NOT_FOUND_MESSAGE = "La asignación de asesor solicitada no existe."
COMPANY_INACTIVE_MESSAGE = "La empresa está inactiva: no se pueden registrar ni cambiar sus asesores."


class SQLAlchemyAdvisorAssignmentRepository:
    """Persistencia de asignaciones de asesor."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def end_read(self) -> None:
        if self.session.in_transaction():
            self.session.rollback()

    def get_by_id(self, assignment_id: UUID) -> AdvisorAssignment | None:
        model = self.session.get(CompanyAdvisorAssignmentModel, assignment_id, populate_existing=True)

        return None if model is None else to_advisor_assignment(model)

    def find_active_primary(self, company_id: UUID) -> AdvisorAssignment | None:
        model = self.session.scalar(
            select(CompanyAdvisorAssignmentModel).where(
                CompanyAdvisorAssignmentModel.company_id == company_id,
                CompanyAdvisorAssignmentModel.status == "ACTIVE",
                CompanyAdvisorAssignmentModel.is_primary.is_(True),
            )
        )

        return None if model is None else to_advisor_assignment(model)

    def exists_active_person(self, company_id: UUID, person_identity_id: UUID) -> bool:
        return (
            self.session.scalar(
                select(CompanyAdvisorAssignmentModel.id)
                .where(
                    CompanyAdvisorAssignmentModel.company_id == company_id,
                    CompanyAdvisorAssignmentModel.person_identity_id == person_identity_id,
                    CompanyAdvisorAssignmentModel.status == "ACTIVE",
                )
                .limit(1)
            )
            is not None
        )

    def list_by_company(
        self,
        company_id: UUID,
        filters: AdvisorFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[AdvisorAssignment]:
        conditions = [CompanyAdvisorAssignmentModel.company_id == company_id]

        if filters.status is not None:
            conditions.append(CompanyAdvisorAssignmentModel.status == filters.status)

        if filters.is_primary is not None:
            conditions.append(CompanyAdvisorAssignmentModel.is_primary.is_(filters.is_primary))

        if filters.person_identity_id is not None:
            conditions.append(CompanyAdvisorAssignmentModel.person_identity_id == filters.person_identity_id)

        total_records = self.session.scalar(
            select(func.count()).select_from(CompanyAdvisorAssignmentModel).where(*conditions)
        ) or 0
        models = self.session.scalars(
            select(CompanyAdvisorAssignmentModel)
            .where(*conditions)
            .order_by(
                CompanyAdvisorAssignmentModel.valid_from.desc(),
                CompanyAdvisorAssignmentModel.id,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return PageResult(
            items=[to_advisor_assignment(model) for model in models],
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
    ) -> AdvisorAssignment:
        self._lock_active_company(company_id)
        model = self._new(company_id, values, actor_id)
        self.session.add(model)
        self._commit()

        return self._reload(model.id)

    def close(
        self,
        assignment_id: UUID,
        *,
        expected_version: int,
        valid_to: datetime,
        actor_id: str,
    ) -> AdvisorAssignment:
        model = load_for_update(
            self.session,
            CompanyAdvisorAssignmentModel,
            assignment_id,
            expected_version=expected_version,
            not_found_message=NOT_FOUND_MESSAGE,
        )

        if model.status != "ACTIVE":
            self.session.rollback()
            raise InvalidStatusTransitionError("La asignación de asesor ya está cerrada.")

        model.status = "INACTIVE"
        model.valid_to = valid_to
        model.updated_by = actor_id
        self._commit()

        return self._reload(assignment_id)

    def change_primary(
        self,
        company_id: UUID,
        *,
        current_assignment_id: UUID,
        expected_version: int,
        person_identity_id: UUID,
        effective_at: datetime,
        actor_id: str,
    ) -> tuple[AdvisorAssignment, AdvisorAssignment]:
        """Cierra la principal vigente y crea la nueva en la misma transacción (FR-053)."""
        self._lock_active_company(company_id)
        current = self.session.get(
            CompanyAdvisorAssignmentModel,
            current_assignment_id,
            with_for_update=True,
            populate_existing=True,
        )

        if (
            current is None
            or current.company_id != company_id
            or current.status != "ACTIVE"
            or not current.is_primary
        ):
            self.session.rollback()
            raise PrimaryAdvisorMismatchError(field="current_assignment_id")

        if current.version != expected_version:
            self.session.rollback()
            raise VersionConflictError

        if effective_at <= current.valid_from:
            self.session.rollback()
            raise InvalidValidityPeriodError(
                "El cambio debe ser posterior al inicio de la asignación vigente.",
                field="effective_at",
            )

        current.status = "INACTIVE"
        current.valid_to = effective_at
        current.updated_by = actor_id
        # El cierre se escribe antes de insertar la nueva para liberar el índice parcial.
        self.session.flush()

        created = self._new(
            company_id,
            {"person_identity_id": person_identity_id, "is_primary": True, "valid_from": effective_at},
            actor_id,
        )
        self.session.add(created)
        self._commit()

        return self._reload(current_assignment_id), self._reload(created.id)

    def _new(self, company_id: UUID, values: dict[str, Any], actor_id: str) -> CompanyAdvisorAssignmentModel:
        return CompanyAdvisorAssignmentModel(
            id=uuid4(),
            company_id=company_id,
            status="ACTIVE",
            assigned_by=actor_id,
            created_by=actor_id,
            updated_by=actor_id,
            **values,
        )

    def _lock_active_company(self, company_id: UUID) -> None:
        status = self.session.execute(
            select(CompanyModel.status)
            .where(CompanyModel.id == company_id)
            .with_for_update(read=True)
        ).scalar_one_or_none()

        if status is None:
            self.session.rollback()
            raise NotFoundError("La empresa solicitada no existe.")

        if status != "ACTIVE":
            self.session.rollback()
            raise CompanyInactiveError(COMPANY_INACTIVE_MESSAGE)

    def _commit(self) -> None:
        commit_or_translate(
            self.session,
            duplicates={
                UNIQUE_PRIMARY: PrimaryAdvisorExistsError,
                UNIQUE_PERSON: DuplicateAdvisorAssignmentError(field="person_identity_id"),
            },
        )

    def _reload(self, assignment_id: UUID) -> AdvisorAssignment:
        assignment = self.get_by_id(assignment_id)
        self.end_read()

        if assignment is None:  # pragma: no cover - la fila acaba de confirmarse
            raise NotFoundError(NOT_FOUND_MESSAGE)

        return assignment


def to_advisor_assignment(model: CompanyAdvisorAssignmentModel) -> AdvisorAssignment:
    return AdvisorAssignment(
        id=model.id,
        company_id=model.company_id,
        person_identity_id=model.person_identity_id,
        is_primary=model.is_primary,
        status=model.status,
        valid_from=model.valid_from,
        valid_to=model.valid_to,
        assigned_by=model.assigned_by,
        version=model.version,
        created_by=model.created_by,
        updated_by=model.updated_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
