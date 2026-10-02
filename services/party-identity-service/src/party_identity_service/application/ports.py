"""Contratos (puertos) usados por la capa de aplicación."""

from datetime import date, datetime
from typing import Any, Protocol
from uuid import UUID

from party_identity_service.application.identification_rules import (
    IdentificationRule,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.identification_type_rule import (
    IdentificationSigla,
    IdentificationType,
    IdentificationTypeRule,
    PartyKind,
)
from party_identity_service.domain.organization_identity import (
    OrganizationIdentificationType,
    OrganizationIdentity,
)
from party_identity_service.domain.person_identity import (
    IdentityStatus,
    PersonIdentificationType,
    PersonIdentity,
    PersonVerificationStatus,
)


class CountryDirectory(Protocol):
    """Puerto único hacia Geography Service (FR-044).

    En producción e integración lo implementa el adaptador HTTP; en las pruebas
    se sustituye por un doble inyectado desde `tests/`.
    """

    def exists(
        self,
        country_id: UUID,
    ) -> bool:
        """Indica si el país existe en Geography Service.

        Raises:
            DependencyUnavailableError: Si no es posible validar.
        """
        ...

    def find_id_by_iso3(
        self,
        iso3_code: str,
    ) -> UUID:
        """Resuelve el UUID de un país por su código ISO alfa-3.

        Raises:
            CountryNotFoundError: Si no existe exactamente un país.
            DependencyUnavailableError: Si no es posible consultar.
        """
        ...


class PersonIdentityRepository(Protocol):
    """Define operaciones de persistencia para identidades de personas."""

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        identification_country_id: UUID | None,
        identification_type: PersonIdentificationType | None,
        verification_status: PersonVerificationStatus | None,
        status: IdentityStatus,
    ) -> PageResult[PersonIdentity]:
        """Obtiene una página filtrada de identidades de persona."""
        ...

    def get_by_id(
        self,
        person_identity_id: UUID,
    ) -> PersonIdentity | None:
        """Obtiene una identidad de persona por identificador."""
        ...

    def create(
        self,
        *,
        identification_country_id: UUID,
        identification_type: PersonIdentificationType,
        identification_number: str,
        first_name: str,
        middle_name: str | None,
        last_name: str,
        second_last_name: str | None,
        birth_date: date | None,
        verification_status: PersonVerificationStatus,
        actor_id: str,
    ) -> PersonIdentity:
        """Crea una identidad global de persona.

        Raises:
            DuplicateIdentificationError: Si la identificación ya existe.
        """
        ...

    def update(
        self,
        person_identity_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> PersonIdentity:
        """Modifica los campos indicados con control de versión.

        Raises:
            NotFoundError, VersionConflictError, DuplicateIdentificationError.
        """
        ...

    def set_status(
        self,
        person_identity_id: UUID,
        *,
        expected_version: int,
        status: IdentityStatus,
        actor_id: str,
    ) -> PersonIdentity:
        """Cambia el estado de uso con control de versión.

        Raises:
            NotFoundError, VersionConflictError.
        """
        ...


class OrganizationIdentityRepository(Protocol):
    """Define operaciones de persistencia para identidades de organizaciones."""

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        country_id: UUID | None,
        identification_type: OrganizationIdentificationType | None,
        registration_status: str | None,
        status: IdentityStatus,
    ) -> PageResult[OrganizationIdentity]:
        """Obtiene una página filtrada de identidades de organización."""
        ...

    def get_by_id(
        self,
        organization_identity_id: UUID,
    ) -> OrganizationIdentity | None:
        """Obtiene una identidad de organización por identificador."""
        ...

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
        """Crea una identidad global de organización.

        Raises:
            DuplicateIdentificationError: Si la identificación ya existe.
        """
        ...

    def update(
        self,
        organization_identity_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> OrganizationIdentity:
        """Modifica los campos indicados con control de versión."""
        ...

    def set_status(
        self,
        organization_identity_id: UUID,
        *,
        expected_version: int,
        status: IdentityStatus,
        actor_id: str,
    ) -> OrganizationIdentity:
        """Cambia el estado de uso con control de versión."""
        ...


class IdentificationTypeRuleRepository(Protocol):
    """Define operaciones de persistencia para reglas de identificación."""

    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        party_kind: PartyKind | None,
        country_id: UUID | None,
        identification_type: IdentificationType | None,
        sigla: IdentificationSigla | None,
        is_active: bool | None,
    ) -> PageResult[IdentificationTypeRule]:
        """Obtiene una página filtrada de reglas de identificación."""
        ...

    def get_by_id(
        self,
        rule_id: UUID,
    ) -> IdentificationTypeRule | None:
        """Obtiene una regla por identificador."""
        ...

    def create(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
        identification_type: IdentificationType,
        sigla: IdentificationSigla,
        number_pattern: str,
        number_pattern_description: str,
        example_value: str | None,
        min_age_years: int | None,
        max_age_years: int | None,
        valid_from: datetime | None,
        valid_to: datetime | None,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Crea una regla activa.

        Raises:
            DuplicateActiveRuleError: Si ya existe una activa con la misma llave.
        """
        ...

    def update(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Modifica en sitio los campos no semánticos de una regla."""
        ...

    def create_version(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        number_pattern: str,
        number_pattern_description: str,
        example_value: str | None,
        min_age_years: int | None,
        max_age_years: int | None,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Cierra la regla vigente y crea su sucesora en una transacción.

        Raises:
            NotFoundError, VersionConflictError, InvalidStatusTransitionError,
            DuplicateActiveRuleError.
        """
        ...

    def deactivate(
        self,
        rule_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> IdentificationTypeRule:
        """Retira una regla (`is_active = FALSE` y `valid_to`)."""
        ...

    def list_active_rules_by_sigla(
        self,
        *,
        party_kind: PartyKind,
        country_id: UUID,
        sigla: IdentificationSigla,
    ) -> list[IdentificationRule]:
        """Obtiene las reglas activas y vigentes por país y sigla."""
        ...


# Puertos de la Fase B (integraciones y repositorios): definidos en su propio
# módulo y reexportados aquí como punto único de los contratos de aplicación.
from party_identity_service.application.phase_b_ports import (  # noqa: E402,F401
    BusinessSectorRepository,
    ContactPersonRepository,
    ContactProfileRepository,
    LegalRepresentativeRepository,
    LocationDirectory,
    LocationRecord,
    MembershipResolver,
    OrganizationBusinessSectorRepository,
)
