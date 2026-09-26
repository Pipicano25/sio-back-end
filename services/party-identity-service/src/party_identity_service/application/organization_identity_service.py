"""Casos de uso para identidades globales de organizaciones."""

import logging
from uuid import UUID

from party_identity_service.application.exceptions import (
    CountryNotFoundError,
    InvalidStatusTransitionError,
    NotFoundError,
    VersionConflictError,
)
from party_identity_service.application.identification_rules import (
    match_identification_number,
    normalize_code,
    normalize_identification_number,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.application.ports import (
    CountryDirectory,
    IdentificationTypeRuleRepository,
    OrganizationIdentityRepository,
)
from party_identity_service.domain.masking import mask_identification_number
from party_identity_service.domain.organization_identity import (
    OrganizationIdentificationType,
    OrganizationIdentity,
)
from party_identity_service.domain.person_identity import IdentityStatus

logger = logging.getLogger("party_identity_service")

PARTY_KIND = "ORGANIZATION"
IDENTIFICATION_FIELDS = (
    "country_id",
    "identification_type",
    "identification_number",
)


class OrganizationIdentityService:
    """Orquesta casos de uso de identidades de organizaciones."""

    def __init__(
        self,
        repository: OrganizationIdentityRepository,
        identification_rule_repository: IdentificationTypeRuleRepository,
        country_directory: CountryDirectory,
    ) -> None:
        """Inicializa el servicio de aplicación."""
        self.repository = repository
        self.identification_rule_repository = identification_rule_repository
        self.country_directory = country_directory

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        country_id: UUID | None = None,
        identification_type: OrganizationIdentificationType | None = None,
        registration_status: str | None = None,
        status: IdentityStatus = "ACTIVE",
    ) -> PageResult[OrganizationIdentity]:
        """Obtiene organizaciones; por defecto solo `ACTIVE` (DS-02)."""
        return self.repository.list_all(
            page=page,
            page_size=page_size,
            search=search,
            country_id=country_id,
            identification_type=(
                normalize_code(identification_type)
                if identification_type
                else None
            ),
            registration_status=registration_status,
            status=status,
        )

    def get_by_id(
        self,
        organization_identity_id: UUID,
    ) -> OrganizationIdentity:
        """Obtiene una organización en cualquier estado.

        Raises:
            NotFoundError: Si no existe.
        """
        organization_identity = self.repository.get_by_id(
            organization_identity_id,
        )

        if organization_identity is None:
            raise NotFoundError("La organización solicitada no existe.")

        return organization_identity

    def create(
        self,
        *,
        country_id: UUID,
        identification_type: OrganizationIdentificationType,
        identification_number: str,
        legal_name: str,
        trade_name: str | None,
        organization_type: str | None,
        registration_status: str | None,
        website: str | None,
        actor_id: str,
    ) -> OrganizationIdentity:
        """Crea una identidad global de organización."""
        identification_type = normalize_code(identification_type)
        identification_number = normalize_identification_number(
            identification_number,
        )
        self._validate_country(country_id)
        self._validate_identification_number(
            country_id=country_id,
            identification_type=identification_type,
            identification_number=identification_number,
        )

        organization_identity = self.repository.create(
            country_id=country_id,
            identification_type=identification_type,
            identification_number=identification_number,
            legal_name=legal_name,
            trade_name=trade_name,
            organization_type=organization_type,
            registration_status=registration_status,
            website=website,
            actor_id=actor_id,
        )
        logger.info(
            "Organización creada id=%s identificacion=%s %s",
            organization_identity.id,
            identification_type,
            mask_identification_number(identification_number),
        )

        return organization_identity

    def update(
        self,
        organization_identity_id: UUID,
        *,
        expected_version: int,
        country_id: UUID,
        identification_type: OrganizationIdentificationType,
        identification_number: str,
        legal_name: str,
        trade_name: str | None,
        organization_type: str | None,
        registration_status: str | None,
        website: str | None,
        actor_id: str,
    ) -> OrganizationIdentity:
        """Modifica una organización (FR-033, FR-034, FR-029)."""
        current = self.get_by_id(organization_identity_id)

        if current.version != expected_version:
            raise VersionConflictError

        requested = {
            "country_id": country_id,
            "identification_type": normalize_code(identification_type),
            "identification_number": normalize_identification_number(
                identification_number,
            ),
            "legal_name": legal_name,
            "trade_name": trade_name,
            "organization_type": organization_type,
            "registration_status": registration_status,
            "website": website,
        }
        changes = {
            field: value
            for field, value in requested.items()
            if getattr(current, field) != value
        }

        if not changes:
            return current

        if any(field in changes for field in IDENTIFICATION_FIELDS):
            self._validate_country(requested["country_id"])
            self._validate_identification_number(
                country_id=requested["country_id"],
                identification_type=requested["identification_type"],
                identification_number=requested["identification_number"],
            )

        return self.repository.update(
            organization_identity_id,
            expected_version=expected_version,
            values=changes,
            actor_id=actor_id,
        )

    def deactivate(
        self,
        organization_identity_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> OrganizationIdentity:
        """Inactiva una organización sin eliminarla (DS-11)."""
        return self._change_status(
            organization_identity_id,
            expected_version=expected_version,
            target="INACTIVE",
            actor_id=actor_id,
        )

    def reactivate(
        self,
        organization_identity_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> OrganizationIdentity:
        """Reactiva una organización inactiva (DS-11)."""
        return self._change_status(
            organization_identity_id,
            expected_version=expected_version,
            target="ACTIVE",
            actor_id=actor_id,
        )

    def _change_status(
        self,
        organization_identity_id: UUID,
        *,
        expected_version: int,
        target: IdentityStatus,
        actor_id: str,
    ) -> OrganizationIdentity:
        current = self.get_by_id(organization_identity_id)

        if current.version != expected_version:
            raise VersionConflictError

        if current.status == target:
            raise InvalidStatusTransitionError(
                f"La organización ya se encuentra en estado {target}."
            )

        return self.repository.set_status(
            organization_identity_id,
            expected_version=expected_version,
            status=target,
            actor_id=actor_id,
        )

    def _validate_country(
        self,
        country_id: UUID,
    ) -> None:
        """Valida que el país exista en Geography Service."""
        if not self.country_directory.exists(country_id):
            raise CountryNotFoundError

    def _validate_identification_number(
        self,
        *,
        country_id: UUID,
        identification_type: str,
        identification_number: str,
    ) -> None:
        """Valida el número contra las reglas activas de la sigla (DS-03)."""
        rules = self.identification_rule_repository.list_active_rules_by_sigla(
            party_kind=PARTY_KIND,
            country_id=country_id,
            sigla=identification_type,
        )
        match_identification_number(
            rules,
            identification_number,
        )
