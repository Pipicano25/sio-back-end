"""Casos de uso de asesores de empresa (US5 de la feature 005; FR-050 a FR-058; DS-13, DS-15).

- Varios asesores vigentes, uno solo principal.
- La `PersonIdentity` se valida al crear una asignación y en `change-primary`
  para la persona nueva, **antes** de escribir y sin transacción abierta.
- Una asignación cerrada es inmutable: no se modifica, no se reabre ni cambia
  su `person_identity_id` (C-12).
- Las vigencias se calculan con el reloj de la aplicación (`domain/validity.py`).
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.exceptions import (
    CompanyInactiveError,
    DuplicateAdvisorAssignmentError,
    InvalidStatusTransitionError,
    InvalidValidityPeriodError,
    NoActivePrimaryAdvisorError,
    NotFoundError,
    PrimaryAdvisorExistsError,
    PrimaryAdvisorMismatchError,
    VersionConflictError,
)
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.ports import (
    AdvisorAssignmentRepository,
    AdvisorFilters,
    CompanyRepository,
    PersonDirectory,
)
from operational_context_service.application.reference_validation import validate_person
from operational_context_service.domain.entities import AdvisorAssignment
from operational_context_service.domain.status import ACTIVE
from operational_context_service.domain.validity import resolve_end, resolve_start, utc_now
from operational_context_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

NOT_FOUND_MESSAGE = "La asignación de asesor solicitada no existe."
COMPANY_INACTIVE_MESSAGE = "La empresa está inactiva: no se pueden registrar ni cambiar sus asesores."


class AdvisorAssignmentService:
    """Orquesta los casos de uso de asesores."""

    def __init__(
        self,
        repository: AdvisorAssignmentRepository,
        companies: CompanyRepository,
        persons: PersonDirectory,
        clock=utc_now,
    ) -> None:
        self.repository = repository
        self.companies = companies
        self.persons = persons
        self.clock = clock

    # ------------------------------------------------------------------ consultas

    def get(self, scope: AccessScope, assignment_id: UUID) -> AdvisorAssignment:
        assignment = self.repository.get_by_id(assignment_id)
        self.repository.end_read()

        if assignment is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)

        scope.ensure_company_visible(assignment.company_id, not_found_message=NOT_FOUND_MESSAGE)

        return assignment

    def list(
        self,
        scope: AccessScope,
        company_id: UUID,
        filters: AdvisorFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[AdvisorAssignment]:
        """Historial ordenado por vigencia; sin filtro de estado devuelve todas (FR-056)."""
        self._visible_company(scope, company_id)
        result = self.repository.list_by_company(company_id, filters, page=page, page_size=page_size)
        self.repository.end_read()

        return result

    # ------------------------------------------------------------------ escritura

    def create(
        self,
        scope: AccessScope,
        company_id: UUID,
        *,
        person_identity_id: UUID,
        is_primary: bool,
        valid_from: datetime | None,
        actor_id: str,
    ) -> AdvisorAssignment:
        """Registra un asesor (FR-050 a FR-052)."""
        company = self._visible_company(scope, company_id)

        if company.status != ACTIVE:
            raise CompanyInactiveError(COMPANY_INACTIVE_MESSAGE)

        start = resolve_start(valid_from, now=self.clock(), field="valid_from")

        if is_primary and self.repository.find_active_primary(company_id) is not None:
            self.repository.end_read()
            raise PrimaryAdvisorExistsError(field="is_primary")

        if self.repository.exists_active_person(company_id, person_identity_id):
            self.repository.end_read()
            raise DuplicateAdvisorAssignmentError(field="person_identity_id")

        self.repository.end_read()
        validate_person(self.persons, person_identity_id)

        assignment = self.repository.create_in_active_company(
            company_id,
            {"person_identity_id": person_identity_id, "is_primary": is_primary, "valid_from": start},
            actor_id=actor_id,
        )
        logger.info("Asesor registrado id=%s empresa=%s principal=%s", assignment.id, company_id, is_primary)

        return assignment

    def close(
        self,
        scope: AccessScope,
        assignment_id: UUID,
        *,
        expected_version: int,
        valid_to: datetime | None,
        actor_id: str,
    ) -> AdvisorAssignment:
        """Cierra una asignación vigente; sin proveedores (FR-054)."""
        current = self.get(scope, assignment_id)

        if current.version != expected_version:
            raise VersionConflictError

        if current.status != ACTIVE:
            raise InvalidStatusTransitionError("La asignación de asesor ya está cerrada.")

        end = resolve_end(valid_to, valid_from=current.valid_from, now=self.clock(), field="valid_to")

        return self.repository.close(assignment_id, expected_version=expected_version, valid_to=end, actor_id=actor_id)

    def change_primary(
        self,
        scope: AccessScope,
        company_id: UUID,
        *,
        current_assignment_id: UUID,
        expected_version: int,
        person_identity_id: UUID,
        effective_at: datetime | None,
        actor_id: str,
    ) -> tuple[AdvisorAssignment, AdvisorAssignment]:
        """Cambia el asesor principal de forma atómica (FR-053, DS-13, C-12)."""
        company = self._visible_company(scope, company_id)

        if company.status != ACTIVE:
            raise CompanyInactiveError(COMPANY_INACTIVE_MESSAGE)

        primary = self.repository.find_active_primary(company_id)

        if primary is None:
            self.repository.end_read()
            raise NoActivePrimaryAdvisorError

        if primary.id != current_assignment_id:
            self.repository.end_read()
            raise PrimaryAdvisorMismatchError(field="current_assignment_id")

        if primary.version != expected_version:
            self.repository.end_read()
            raise VersionConflictError

        start = resolve_start(effective_at, now=self.clock(), field="effective_at")

        if start <= primary.valid_from:
            self.repository.end_read()
            raise InvalidValidityPeriodError(
                "El cambio debe ser posterior al inicio de la asignación vigente.",
                field="effective_at",
            )

        if self.repository.exists_active_person(company_id, person_identity_id):
            self.repository.end_read()
            raise DuplicateAdvisorAssignmentError(field="person_identity_id")

        self.repository.end_read()

        # La persona nueva se valida antes de escribir (DS-15, C-12).
        validate_person(self.persons, person_identity_id)

        closed, created = self.repository.change_primary(
            company_id,
            current_assignment_id=current_assignment_id,
            expected_version=expected_version,
            person_identity_id=person_identity_id,
            effective_at=start,
            actor_id=actor_id,
        )
        logger.info(
            "Asesor principal cambiado empresa=%s cerrada=%s creada=%s",
            company_id,
            closed.id,
            created.id,
        )

        return closed, created

    # ------------------------------------------------------------------ apoyo

    def _visible_company(self, scope: AccessScope, company_id: UUID):
        company = self.companies.get_by_id(company_id)
        self.companies.end_read()

        if company is None:
            raise NotFoundError("La empresa solicitada no existe.")

        scope.ensure_company_visible(company_id)

        return company
