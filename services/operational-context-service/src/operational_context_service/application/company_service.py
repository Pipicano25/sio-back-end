"""Casos de uso de empresas (US2, US3, US5, US6).

Orden de trabajo (R-05, R-09): lecturas y validaciones locales → cierre de la
transacción de lectura → llamadas a Party Identity y Geography **sin**
transacción abierta → transacción de escritura que revalida versión y
unicidad.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from operational_context_service.application.exceptions import (
    DuplicateOrganizationIdentityError,
    InvalidStatusTransitionError,
    NotFoundError,
    OrganizationIdentityInactiveError,
    OrganizationIdentityNotFoundError,
    VersionConflictError,
)
from operational_context_service.application.location_validation import (
    Location,
    log_rejected_reference,
    validate_location,
)
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.ports import (
    CompanyFilters,
    CompanyRepository,
    GeographyDirectory,
    OrganizationDirectory,
)
from operational_context_service.domain.currency import normalize_currency
from operational_context_service.domain.entities import Company
from operational_context_service.domain.location import validate_coordinates
from operational_context_service.domain.status import ACTIVE, INACTIVE, EntityStatus
from operational_context_service.domain.timezone import normalize_timezone
from operational_context_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

COMPANY_FIELDS = (
    "organization_identity_id",
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
    "default_currency",
)


def _location_of(values: dict[str, Any] | Company) -> Location:
    get = values.get if isinstance(values, dict) else lambda key: getattr(values, key)
    return Location(
        country_id=get("country_id"),
        administrative_division_id=get("administrative_division_id"),
        city_id=get("city_id"),
    )


class CompanyService:
    """Orquesta los casos de uso de empresas."""

    def __init__(
        self,
        repository: CompanyRepository,
        organizations: OrganizationDirectory,
        geography: GeographyDirectory,
    ) -> None:
        self.repository = repository
        self.organizations = organizations
        self.geography = geography

    # ------------------------------------------------------------------ consultas

    def get(self, company_id: UUID) -> Company:
        """Obtiene una empresa en cualquier estado (contrato Provider)."""
        company = self.repository.get_by_id(company_id)
        self.repository.end_read()

        if company is None:
            raise NotFoundError("La empresa solicitada no existe.")

        return company

    def list(self, filters: CompanyFilters, *, page: int, page_size: int) -> PageResult[Company]:
        """Colección paginada; por defecto solo `ACTIVE` (FR-015)."""
        result = self.repository.list_all(filters, page=page, page_size=page_size)
        self.repository.end_read()

        return result

    # ------------------------------------------------------------------ escritura

    def create(self, data: dict[str, Any], *, actor_id: str) -> Company:
        """Registra una empresa vinculada a su organización (FR-010 a FR-014)."""
        values = self._normalize(data)

        if self.repository.exists_organization(values["organization_identity_id"]):
            self.repository.end_read()
            raise DuplicateOrganizationIdentityError(field="organization_identity_id")

        self.repository.end_read()

        # Llamadas externas sin transacción abierta (R-09).
        self._validate_organization(values["organization_identity_id"])
        validate_location(_location_of(values), None, self.geography)

        company = self.repository.create(values, actor_id=actor_id)
        logger.info("Empresa creada id=%s organizacion=%s", company.id, company.organization_identity_id)

        return company

    def update(
        self,
        company_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int,
        actor_id: str,
    ) -> Company:
        """Modifica una empresa (FR-016, FR-063, DS-06)."""
        current = self.get(company_id)

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

        if "organization_identity_id" in changes:
            duplicated = self.repository.exists_organization(
                values["organization_identity_id"],
                exclude_company_id=company_id,
            )
            self.repository.end_read()

            if duplicated:
                raise DuplicateOrganizationIdentityError(field="organization_identity_id")

            self._validate_organization(values["organization_identity_id"])

        validate_location(_location_of(values), _location_of(current), self.geography)

        return self.repository.update(
            company_id,
            expected_version=expected_version,
            values=changes,
            actor_id=actor_id,
        )

    def deactivate(self, company_id: UUID, *, expected_version: int, actor_id: str) -> Company:
        """Inactiva sin eliminar y sin modificar sus sucursales (DS-07, DS-11)."""
        return self._change_status(company_id, INACTIVE, expected_version, actor_id)

    def reactivate(self, company_id: UUID, *, expected_version: int, actor_id: str) -> Company:
        """Reactiva una empresa inactiva (DS-11)."""
        return self._change_status(company_id, ACTIVE, expected_version, actor_id)

    # ------------------------------------------------------------------ apoyo

    def _change_status(
        self,
        company_id: UUID,
        target: EntityStatus,
        expected_version: int,
        actor_id: str,
    ) -> Company:
        current = self.get(company_id)

        if current.version != expected_version:
            raise VersionConflictError

        if current.status == target:
            raise InvalidStatusTransitionError(f"La empresa ya se encuentra en estado {target}.")

        company = self.repository.update(
            company_id,
            expected_version=expected_version,
            values={"status": target},
            actor_id=actor_id,
        )
        logger.info("Empresa id=%s cambió a estado %s", company_id, target)

        return company

    def _validate_organization(self, organization_identity_id: UUID) -> None:
        organization = self.organizations.get_organization(organization_identity_id)

        if organization is None:
            error = OrganizationIdentityNotFoundError(field="organization_identity_id")
            log_rejected_reference(error, organization_identity_id)
            raise error

        if organization.status != ACTIVE:
            error = OrganizationIdentityInactiveError(field="organization_identity_id")
            log_rejected_reference(error, organization_identity_id)
            raise error

    @staticmethod
    def _normalize(data: dict[str, Any]) -> dict[str, Any]:
        values = {field: data.get(field) for field in COMPANY_FIELDS}
        values["timezone"] = normalize_timezone(values["timezone"])
        values["default_currency"] = normalize_currency(values["default_currency"])
        validate_coordinates(values["latitude"], values["longitude"])

        return values
