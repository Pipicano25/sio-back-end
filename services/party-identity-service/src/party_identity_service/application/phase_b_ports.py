"""Puertos de la Fase B: integraciones externas y repositorios.

La capa de aplicación depende solo de estos protocolos; las implementaciones
viven en `infrastructure/` y las pruebas inyectan dobles por los mismos puertos
(Principio XV, FR-038, FR-101). Se reexportan desde `application.ports`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from party_identity_service.application.pagination import PageResult
from party_identity_service.domain.business_sector import (
    BusinessSector,
    OrganizationBusinessSector,
    SectorStatus,
)
from party_identity_service.domain.contact import (
    ContactData,
    ContactPerson,
    ContactProfile,
    RelationState,
)
from party_identity_service.domain.legal_representative import (
    LegalRepresentative,
    RepresentativeType,
)

LocationStatus = Literal["ACTIVE", "INACTIVE"]


# --------------------------------------------------------------------------
# Integraciones externas
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LocationRecord:
    """Datos de un nivel geográfico leídos de Geography (no se persisten)."""

    id: UUID
    status: LocationStatus
    country_id: UUID | None = None
    administrative_division_id: UUID | None = None


class LocationDirectory(Protocol):
    """Puerto hacia Geography para las direcciones de los perfiles (R-07).

    Cada método devuelve `None` si el nivel no existe.

    Raises:
        DependencyUnavailableError: (`dependency="geography"`) si no es posible consultar.
    """

    def get_country(self, country_id: UUID) -> LocationRecord | None: ...

    def get_administrative_division(self, division_id: UUID) -> LocationRecord | None: ...

    def get_city(self, city_id: UUID) -> LocationRecord | None: ...


class MembershipResolver(Protocol):
    """Puerto hacia Operational Context (vía técnica de `operational-access`, R-06).

    Resuelve el `ApplicationUser` del usuario autenticado en la empresa.

    Raises:
        CompanyNotFoundError: La empresa no existe.
        CompanyInactiveError: La empresa está inactiva.
        ConfirmationMembershipInvalidError: Sin membresía `ACTIVE` (con `reason`).
        DependencyUnavailableError: Operational Context o Keycloak no disponibles.
    """

    def resolve(self, *, company_id: UUID, keycloak_user_id: str) -> UUID: ...


# --------------------------------------------------------------------------
# Repositorios
# --------------------------------------------------------------------------


class ContactProfileRepository(Protocol):
    """Perfiles versionados de un tipo de parte (persona u organización)."""

    def get_active(self, owner_id: UUID) -> ContactProfile | None: ...

    def get_version(self, profile_id: UUID) -> ContactProfile | None: ...

    def list_versions(self, owner_id: UUID, *, page: int, page_size: int) -> PageResult[ContactProfile]: ...

    def has_history(self, owner_id: UUID) -> bool: ...

    def replace(
        self,
        owner_id: UUID,
        *,
        expected_active_id: UUID | None,
        expected_version: int | None,
        data: ContactData,
        confirmed_by_company_id: UUID,
        confirmed_by_user_id: UUID,
        actor_id: str,
    ) -> ContactProfile:
        """Bloquea al propietario, revalida la vigente y cierra + crea en una transacción.

        Raises:
            VersionConflictError: La vigente cambió desde la lectura previa.
        """
        ...

    def close(self, owner_id: UUID, *, expected_version: int, actor_id: str) -> ContactProfile:
        """Cierra la vigente sin reemplazo bajo bloqueo del propietario.

        Raises:
            ContactProfileNotFoundError: Nunca existió perfil.
            ContactProfileAlreadyClosedError: No hay vigente pero sí historia.
            VersionConflictError: Versión esperada obsoleta.
        """
        ...


class ContactPersonRepository(Protocol):
    def list_by_organization(
        self, organization_id: UUID, *, is_active: bool, page: int, page_size: int
    ) -> PageResult[ContactPerson]: ...

    def get_by_id(self, contact_id: UUID) -> ContactPerson | None: ...

    def create(
        self,
        *,
        organization_id: UUID,
        person_identity_id: UUID | None,
        position: str | None,
        email: str | None,
        phone: str | None,
        is_primary: bool,
        actor_id: str,
    ) -> ContactPerson: ...

    def update(
        self, contact_id: UUID, *, expected_version: int, values: dict[str, Any], actor_id: str
    ) -> ContactPerson: ...

    def set_active(
        self, contact_id: UUID, *, expected_version: int, active: bool, actor_id: str
    ) -> ContactPerson: ...

    def set_primary(self, contact_id: UUID, *, expected_version: int, actor_id: str) -> ContactPerson: ...


class BusinessSectorRepository(Protocol):
    def list_all(
        self,
        *,
        page: int,
        page_size: int,
        classification_system: str | None,
        code: str | None,
        parent_sector_id: UUID | None,
        roots_only: bool,
        status: SectorStatus,
        search: str | None,
    ) -> PageResult[BusinessSector]: ...

    def get_by_id(self, sector_id: UUID) -> BusinessSector | None: ...

    def create(
        self,
        *,
        parent_sector_id: UUID | None,
        classification_system: str,
        code: str,
        name: str,
        description: str | None,
        actor_id: str,
    ) -> BusinessSector: ...

    def update(
        self, sector_id: UUID, *, expected_version: int, values: dict[str, Any], actor_id: str
    ) -> BusinessSector: ...

    def has_active_children(self, sector_id: UUID) -> bool: ...

    def ancestor_ids(self, sector_id: UUID) -> list[UUID]: ...


class OrganizationBusinessSectorRepository(Protocol):
    def list_by_organization(
        self, organization_id: UUID, *, state: RelationState, page: int, page_size: int
    ) -> PageResult[OrganizationBusinessSector]: ...

    def get_by_id(self, assignment_id: UUID) -> OrganizationBusinessSector | None: ...

    def create(
        self,
        *,
        organization_id: UUID,
        sector_id: UUID,
        is_primary: bool,
        valid_from: datetime | None,
        actor_id: str,
    ) -> OrganizationBusinessSector: ...

    def set_primary(
        self, assignment_id: UUID, *, expected_version: int, actor_id: str
    ) -> OrganizationBusinessSector: ...

    def close(self, assignment_id: UUID, *, expected_version: int, actor_id: str) -> OrganizationBusinessSector: ...


class LegalRepresentativeRepository(Protocol):
    def list_by_organization(
        self, organization_id: UUID, *, state: RelationState, page: int, page_size: int
    ) -> PageResult[LegalRepresentative]: ...

    def get_by_id(self, representative_id: UUID) -> LegalRepresentative | None: ...

    def get_active_primary(self, organization_id: UUID) -> LegalRepresentative | None: ...

    def create(
        self,
        *,
        organization_id: UUID,
        person_identity_id: UUID,
        representative_type: RepresentativeType,
        position: str | None,
        valid_from: datetime | None,
        source_document_reference: str | None,
        actor_id: str,
    ) -> LegalRepresentative: ...

    def update(
        self, representative_id: UUID, *, expected_version: int, values: dict[str, Any], actor_id: str
    ) -> LegalRepresentative: ...

    def close(self, representative_id: UUID, *, expected_version: int, actor_id: str) -> LegalRepresentative: ...

    def set_primary(
        self,
        organization_id: UUID,
        *,
        person_identity_id: UUID,
        position: str | None,
        valid_from: datetime | None,
        source_document_reference: str | None,
        current_primary_version: int | None,
        actor_id: str,
    ) -> tuple[LegalRepresentative, bool]:
        """Establece el `PRIMARY` (crea el primero o sustituye el vigente) en una transacción.

        Returns:
            El `PRIMARY` vigente y `True` si se creó una relación nueva.
        """
        ...
