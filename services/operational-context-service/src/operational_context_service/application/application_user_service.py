"""Casos de uso de usuarios operativos (membresías): US1 y US6 de la feature 005.

Orden del alta (T034): empresa visible y `ACTIVE` → duplicado por persona →
cuenta en Keycloak → duplicado por `sub` → persona en Party Identity →
inserción. Las consultas a Keycloak y Party Identity se hacen sin transacción
abierta y tras el primer rechazo no se consulta nada más. La inserción revalida
la empresa (`FOR SHARE`) y la unicidad `ACTIVE` (índices parciales, R-04).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.exceptions import (
    CompanyInactiveError,
    DuplicateMembershipError,
    InvalidStatusTransitionError,
    NotFoundError,
    VersionConflictError,
)
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.ports import (
    ApplicationUserFilters,
    ApplicationUserRepository,
    CompanyRepository,
    IdentityAccountDirectory,
    PersonDirectory,
)
from operational_context_service.application.reference_validation import (
    resolve_account,
    validate_person,
)
from operational_context_service.domain.entities import ApplicationUser
from operational_context_service.domain.status import ACTIVE, INACTIVE
from operational_context_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

NOT_FOUND_MESSAGE = "El usuario operativo solicitado no existe."
COMPANY_NOT_FOUND_MESSAGE = "La empresa solicitada no existe."
MEMBERSHIP_COMPANY_INACTIVE = (
    "La empresa está inactiva: no se pueden registrar ni reactivar sus usuarios operativos."
)


class ApplicationUserService:
    """Orquesta los casos de uso de membresías."""

    def __init__(
        self,
        repository: ApplicationUserRepository,
        companies: CompanyRepository,
        accounts: IdentityAccountDirectory,
        persons: PersonDirectory,
    ) -> None:
        self.repository = repository
        self.companies = companies
        self.accounts = accounts
        self.persons = persons

    # ------------------------------------------------------------------ consultas

    def get(self, scope: AccessScope, application_user_id: UUID, *, lookup_read: bool = True) -> ApplicationUser:
        """Membresía por UUID en cualquier estado, dentro del alcance (FR-072)."""
        user = self.repository.get_by_id(application_user_id)
        self.repository.end_read()

        if user is None:
            raise NotFoundError(NOT_FOUND_MESSAGE)

        scope.ensure_company_visible(
            user.company_id,
            lookup_read=lookup_read,
            not_found_message=NOT_FOUND_MESSAGE,
        )

        return user

    def list(
        self,
        scope: AccessScope,
        company_id: UUID,
        filters: ApplicationUserFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[ApplicationUser]:
        """Membresías de una empresa visible; por defecto solo `ACTIVE`."""
        self._visible_company(scope, company_id)
        result = self.repository.list_by_company(company_id, filters, page=page, page_size=page_size)
        self.repository.end_read()

        return result

    # ------------------------------------------------------------------ escritura

    def create(
        self,
        scope: AccessScope,
        company_id: UUID,
        data: dict[str, Any],
        *,
        actor_id: str,
    ) -> ApplicationUser:
        """Registra una membresía humana validada (FR-010 a FR-019)."""
        company = self._visible_company(scope, company_id)

        if company.status != ACTIVE:
            raise CompanyInactiveError(MEMBERSHIP_COMPANY_INACTIVE)

        person_identity_id: UUID = data["person_identity_id"]

        if self.repository.exists_active(company_id, person_identity_id=person_identity_id):
            self.repository.end_read()
            raise DuplicateMembershipError(
                "Ya existe una membresía activa de esa persona en la empresa.",
                field="person_identity_id",
            )

        self.repository.end_read()

        # Llamadas externas sin transacción abierta.
        account = resolve_account(
            self.accounts,
            keycloak_user_id=data.get("keycloak_user_id"),
            username=data.get("username"),
        )

        if self.repository.exists_active(company_id, keycloak_user_id=account.sub):
            self.repository.end_read()
            raise DuplicateMembershipError(
                "Ya existe una membresía activa de esa cuenta en la empresa.",
                field="keycloak_user_id",
            )

        self.repository.end_read()
        validate_person(self.persons, person_identity_id)

        user = self.repository.create_in_active_company(
            company_id,
            {
                "keycloak_user_id": account.sub,
                "person_identity_id": person_identity_id,
                "display_name": data["display_name"],
                "reference_email": data.get("reference_email"),
            },
            actor_id=actor_id,
        )
        logger.info("Usuario operativo registrado id=%s empresa=%s", user.id, company_id)

        return user

    def update(
        self,
        scope: AccessScope,
        application_user_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int,
        actor_id: str,
    ) -> ApplicationUser:
        """Modifica nombre y correo de referencia; sin proveedores (FR-013)."""
        current = self.get(scope, application_user_id, lookup_read=False)

        if current.version != expected_version:
            raise VersionConflictError

        values = {
            "display_name": data["display_name"],
            "reference_email": data.get("reference_email"),
        }
        changes = {field: value for field, value in values.items() if getattr(current, field) != value}

        if not changes:
            return current

        return self.repository.update(
            application_user_id,
            expected_version=expected_version,
            values=changes,
            actor_id=actor_id,
        )

    def deactivate(
        self,
        scope: AccessScope,
        application_user_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> ApplicationUser:
        """Inactiva solo esta membresía; sin cascadas ni proveedores (FR-014, DS-11)."""
        current = self.get(scope, application_user_id, lookup_read=False)

        if current.version != expected_version:
            raise VersionConflictError

        if current.status == INACTIVE:
            raise InvalidStatusTransitionError("El usuario operativo ya se encuentra en estado INACTIVE.")

        user = self.repository.update(
            application_user_id,
            expected_version=expected_version,
            values={"status": INACTIVE},
            actor_id=actor_id,
        )
        logger.info("Usuario operativo id=%s cambió a estado INACTIVE", application_user_id)

        return user

    def reactivate(
        self,
        scope: AccessScope,
        application_user_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> ApplicationUser:
        """Reactiva revalidando cuenta y persona y la unicidad `ACTIVE` (FR-014, R-14)."""
        current = self.get(scope, application_user_id, lookup_read=False)

        if current.version != expected_version:
            raise VersionConflictError

        if current.status == ACTIVE:
            raise InvalidStatusTransitionError("El usuario operativo ya se encuentra en estado ACTIVE.")

        if current.company_status != ACTIVE:
            raise CompanyInactiveError(MEMBERSHIP_COMPANY_INACTIVE)

        for field, criteria in (
            ("person_identity_id", {"person_identity_id": current.person_identity_id}),
            ("keycloak_user_id", {"keycloak_user_id": current.keycloak_user_id}),
        ):
            if self.repository.exists_active(current.company_id, exclude_id=current.id, **criteria):
                self.repository.end_read()
                raise DuplicateMembershipError(field=field)

        self.repository.end_read()

        resolve_account(self.accounts, keycloak_user_id=current.keycloak_user_id)
        validate_person(self.persons, current.person_identity_id)

        user = self.repository.reactivate_in_active_company(
            application_user_id,
            expected_version=expected_version,
            actor_id=actor_id,
        )
        logger.info("Usuario operativo id=%s cambió a estado ACTIVE", application_user_id)

        return user

    # ------------------------------------------------------------------ apoyo

    def _visible_company(self, scope: AccessScope, company_id: UUID):
        company = self.companies.get_by_id(company_id)
        self.companies.end_read()

        if company is None:
            raise NotFoundError(COMPANY_NOT_FOUND_MESSAGE)

        scope.ensure_company_visible(company_id)

        return company
