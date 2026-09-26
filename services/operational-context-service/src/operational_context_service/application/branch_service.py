"""Casos de uso de sucursales (US4, US5, US6).

Las sucursales nunca consultan Party Identity. Geography solo se consulta si
cambia la ubicación (DS-06) y siempre sin transacción abierta (R-09). El alta y
la reactivación comprueban que la empresa siga `ACTIVE` bajo bloqueo
`FOR SHARE` en la transacción de escritura (RN-09).
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.exceptions import (
    CompanyInactiveError,
    DuplicateBranchCodeError,
    InvalidStatusTransitionError,
    NotFoundError,
    VersionConflictError,
)
from operational_context_service.application.location_validation import (
    Location,
    validate_location,
)
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.ports import (
    BranchFilters,
    BranchRepository,
    CompanyRepository,
    GeographyDirectory,
)
from operational_context_service.domain.branch_code import normalize_code
from operational_context_service.domain.entities import Branch, Company
from operational_context_service.domain.location import validate_coordinates
from operational_context_service.domain.status import ACTIVE, INACTIVE
from operational_context_service.domain.timezone import normalize_timezone
from operational_context_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

BRANCH_NOT_FOUND_MESSAGE = "La sucursal solicitada no existe."

BRANCH_FIELDS = (
    "code",
    "name",
    "email",
    "phone",
    "address_line",
    "country_id",
    "administrative_division_id",
    "city_id",
    "postal_code",
    "latitude",
    "longitude",
    "timezone",
)


def _location_of(values: dict[str, Any] | Branch) -> Location:
    get = values.get if isinstance(values, dict) else lambda key: getattr(values, key)
    return Location(
        country_id=get("country_id"),
        administrative_division_id=get("administrative_division_id"),
        city_id=get("city_id"),
    )


class BranchService:
    """Orquesta los casos de uso de sucursales."""

    def __init__(
        self,
        repository: BranchRepository,
        companies: CompanyRepository,
        geography: GeographyDirectory,
    ) -> None:
        self.repository = repository
        self.companies = companies
        self.geography = geography

    # ------------------------------------------------------------------ consultas

    def get(self, scope: AccessScope, branch_id: UUID, *, lookup_read: bool = True) -> Branch:
        """Obtiene una sucursal en cualquier estado dentro del alcance (contrato Provider).

        Fuera del alcance de su empresa responde igual que si no existiera (DS-06).
        """
        branch = self.repository.get_by_id(branch_id)
        self.repository.end_read()

        if branch is None:
            raise NotFoundError(BRANCH_NOT_FOUND_MESSAGE)

        scope.ensure_company_visible(
            branch.company_id,
            lookup_read=lookup_read,
            not_found_message=BRANCH_NOT_FOUND_MESSAGE,
        )

        return branch

    def list(
        self,
        scope: AccessScope,
        company_id: UUID,
        filters: BranchFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[Branch]:
        """Sucursales de una empresa visible; `404` si no existe o está fuera del alcance."""
        self._get_company(scope, company_id)
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
    ) -> Branch:
        """Registra una sucursal bajo una empresa `ACTIVE` del alcance (FR-020, FR-021)."""
        company = self._get_company(scope, company_id)

        if company.status != ACTIVE:
            raise CompanyInactiveError

        values = self._normalize(data)

        if self.repository.exists_code(company_id, values["code"]):
            self.repository.end_read()
            raise DuplicateBranchCodeError(field="code")

        self.repository.end_read()

        # Llamadas externas sin transacción abierta (R-09).
        validate_location(_location_of(values), None, self.geography)

        branch = self.repository.create_in_active_company(company_id, values, actor_id=actor_id)
        logger.info("Sucursal creada id=%s empresa=%s", branch.id, company_id)

        return branch

    def update(
        self,
        scope: AccessScope,
        branch_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int,
        actor_id: str,
    ) -> Branch:
        """Modifica una sucursal; la empresa es inmutable (FR-022, FR-025)."""
        current = self.get(scope, branch_id, lookup_read=False)

        if current.version != expected_version:
            raise VersionConflictError

        values = self._normalize(data)
        changes = {
            field: value
            for field, value in values.items()
            if getattr(current, field) != value
        }

        if not changes:
            return current

        if "code" in changes:
            duplicated = self.repository.exists_code(
                current.company_id,
                values["code"],
                exclude_branch_id=branch_id,
            )
            self.repository.end_read()

            if duplicated:
                raise DuplicateBranchCodeError(field="code")

        validate_location(_location_of(values), _location_of(current), self.geography)

        return self.repository.update(
            branch_id,
            expected_version=expected_version,
            values=changes,
            actor_id=actor_id,
        )

    def deactivate(
        self,
        scope: AccessScope,
        branch_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> Branch:
        """Inactiva sin eliminar (FR-026, DS-11)."""
        current = self.get(scope, branch_id, lookup_read=False)

        if current.version != expected_version:
            raise VersionConflictError

        if current.status == INACTIVE:
            raise InvalidStatusTransitionError("La sucursal ya se encuentra en estado INACTIVE.")

        branch = self.repository.update(
            branch_id,
            expected_version=expected_version,
            values={"status": INACTIVE},
            actor_id=actor_id,
        )
        logger.info("Sucursal id=%s cambió a estado INACTIVE", branch_id)

        return branch

    def reactivate(
        self,
        scope: AccessScope,
        branch_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> Branch:
        """Reactiva si la empresa sigue `ACTIVE` (FR-026, RN-09)."""
        current = self.get(scope, branch_id, lookup_read=False)

        if current.version != expected_version:
            raise VersionConflictError

        if current.status == ACTIVE:
            raise InvalidStatusTransitionError("La sucursal ya se encuentra en estado ACTIVE.")

        if current.company_status != ACTIVE:
            raise CompanyInactiveError

        branch = self.repository.reactivate_in_active_company(
            branch_id,
            expected_version=expected_version,
            actor_id=actor_id,
        )
        logger.info("Sucursal id=%s cambió a estado ACTIVE", branch_id)

        return branch

    # ------------------------------------------------------------------ apoyo

    def _get_company(self, scope: AccessScope, company_id: UUID) -> Company:
        company = self.companies.get_by_id(company_id)
        self.companies.end_read()

        if company is None:
            raise NotFoundError("La empresa solicitada no existe.")

        scope.ensure_company_visible(company_id)

        return company

    @staticmethod
    def _normalize(data: dict[str, Any]) -> dict[str, Any]:
        values = {field: data.get(field) for field in BRANCH_FIELDS}
        values["code"] = normalize_code(values["code"])

        if values["timezone"] is not None:
            values["timezone"] = normalize_timezone(values["timezone"])

        validate_coordinates(values["latitude"], values["longitude"])

        return values
