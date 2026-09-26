"""Puertos de la capa de aplicación (Principio XV, R-06).

Cada integración con otro microservicio se consume detrás de un puerto; el
adaptador HTTP real vive en `infrastructure/` y las pruebas inyectan dobles.
Los registros devueltos por los proveedores se usan solo en memoria y nunca se
persisten (FR-044).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from operational_context_service.application.pagination import PageResult
from operational_context_service.domain.entities import (
    AdvisorAssignment,
    ApplicationUser,
    Branch,
    Company,
    UserBranch,
)
from operational_context_service.domain.status import EntityStatus


@dataclass(frozen=True, slots=True)
class ExternalRef:
    """Referencia externa mínima: existe y su estado de uso."""

    id: UUID
    status: str


@dataclass(frozen=True, slots=True)
class DivisionRef:
    """División administrativa de Geography, con su país."""

    id: UUID
    status: str
    country_id: UUID


@dataclass(frozen=True, slots=True)
class CityRef:
    """Ciudad de Geography, con su país y su división (puede ser nula)."""

    id: UUID
    status: str
    country_id: UUID
    administrative_division_id: UUID | None


class OrganizationDirectory(Protocol):
    """Consulta de organizaciones en Party Identity Service."""

    def get_organization(self, organization_identity_id: UUID) -> ExternalRef | None:
        """Devuelve la organización o `None` si no existe.

        Raises:
            DependencyUnavailableError: Si no fue posible consultar.
        """


class GeographyDirectory(Protocol):
    """Consulta de países, divisiones y ciudades en Geography Service."""

    def get_country(self, country_id: UUID) -> ExternalRef | None:
        """Devuelve el país o `None` si no existe."""

    def get_administrative_division(self, division_id: UUID) -> DivisionRef | None:
        """Devuelve la división o `None` si no existe."""

    def get_city(self, city_id: UUID) -> CityRef | None:
        """Devuelve la ciudad o `None` si no existe."""


@dataclass(frozen=True, slots=True)
class CompanyFilters:
    """Filtros de la colección de empresas (FR-015)."""

    status: EntityStatus = "ACTIVE"
    organization_identity_id: UUID | None = None
    country_id: UUID | None = None
    city_id: UUID | None = None
    # Alcance (Fase B, R-02): `None` = sin restricción (plataforma); si no, solo
    # estas empresas. Lo fija el servicio, nunca la API.
    company_ids: frozenset[UUID] | None = None


@dataclass(frozen=True, slots=True)
class BranchFilters:
    """Filtros de la colección de sucursales (FR-023)."""

    status: EntityStatus = "ACTIVE"
    city_id: UUID | None = None
    search: str | None = None


class CompanyRepository(Protocol):
    """Persistencia de empresas."""

    def end_read(self) -> None:
        """Cierra la transacción de lectura en curso (R-09)."""

    def get_by_id(self, company_id: UUID) -> Company | None: ...

    def exists_organization(
        self,
        organization_identity_id: UUID,
        *,
        exclude_company_id: UUID | None = None,
    ) -> bool: ...

    def list_all(
        self,
        filters: CompanyFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[Company]: ...

    def create(self, values: dict[str, Any], *, actor_id: str) -> Company: ...

    def update(
        self,
        company_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> Company: ...


class BranchRepository(Protocol):
    """Persistencia de sucursales."""

    def end_read(self) -> None:
        """Cierra la transacción de lectura en curso (R-09)."""

    def get_by_id(self, branch_id: UUID) -> Branch | None: ...

    def exists_code(
        self,
        company_id: UUID,
        code: str,
        *,
        exclude_branch_id: UUID | None = None,
    ) -> bool: ...

    def list_by_company(
        self,
        company_id: UUID,
        filters: BranchFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[Branch]: ...

    def create_in_active_company(
        self,
        company_id: UUID,
        values: dict[str, Any],
        *,
        actor_id: str,
    ) -> Branch: ...

    def update(
        self,
        branch_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> Branch: ...

    def reactivate_in_active_company(
        self,
        branch_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> Branch: ...



# ---------------------------------------------------------------------------
# Fase B (feature 005): Keycloak (solo lectura), personas y repositorios nuevos.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AccountRef:
    """Cuenta de Keycloak vista por la Admin API; solo se persiste `sub` (FR-065)."""

    sub: str
    username: str
    enabled: bool
    is_service_account: bool


class IdentityAccountDirectory(Protocol):
    """Consulta de cuentas en Keycloak con la identidad técnica propia (R-06).

    Todas las operaciones lanzan `DependencyUnavailableError(provider="keycloak")`
    si no fue posible consultar.
    """

    def get_account(self, sub: str) -> AccountRef | None:
        """Cuenta por `sub` o `None` si no existe."""

    def find_account_by_username(self, username: str) -> AccountRef | None:
        """Cuenta por nombre de usuario exacto o `None` si no existe."""

    def get_permission_roles(self, sub: str) -> frozenset[str]:
        """Roles efectivos del cliente `sio-api` de la cuenta (incluidos los de grupos)."""


class PersonDirectory(Protocol):
    """Consulta de personas en Party Identity Service (R-08)."""

    def get_person(self, person_identity_id: UUID) -> ExternalRef | None:
        """Devuelve la persona o `None` si no existe.

        Raises:
            DependencyUnavailableError: Si no fue posible consultar.
        """


@dataclass(frozen=True, slots=True)
class MembershipRef:
    """Membresía mínima usada por el alcance y el acceso operativo."""

    id: UUID
    company_id: UUID
    status: EntityStatus


class MembershipLookup(Protocol):
    """Lecturas de membresía por `sub` (R-01)."""

    def active_company_ids(self, keycloak_user_id: str) -> frozenset[UUID]:
        """Empresas con membresía `ACTIVE` del `sub`."""

    def find_membership(self, company_id: UUID, keycloak_user_id: str) -> MembershipRef | None:
        """La membresía `ACTIVE` del `sub` en la empresa o, si no hay, la más reciente."""


@dataclass(frozen=True, slots=True)
class ApplicationUserFilters:
    """Filtros de la colección de usuarios operativos (FR-015)."""

    status: EntityStatus = "ACTIVE"
    search: str | None = None
    keycloak_user_id: str | None = None
    person_identity_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AdvisorFilters:
    """Filtros del historial de asesores (FR-056); `status=None` = todas."""

    status: EntityStatus | None = None
    is_primary: bool | None = None
    person_identity_id: UUID | None = None


# ---------------------------------------------------------------------------
# Repositorios de la Fase B (T094): la capa de aplicación depende de estas
# abstracciones; las implementaciones SQLAlchemy viven en `infrastructure/`.
# ---------------------------------------------------------------------------


class ApplicationUserRepository(Protocol):
    """Persistencia de membresías (`application_users`)."""

    def end_read(self) -> None:
        """Cierra la transacción de lectura en curso."""

    def get_by_id(self, application_user_id: UUID) -> ApplicationUser | None: ...

    def list_by_subject(self, keycloak_user_id: str) -> list[ApplicationUser]: ...

    def exists_active(
        self,
        company_id: UUID,
        *,
        person_identity_id: UUID | None = None,
        keycloak_user_id: str | None = None,
        exclude_id: UUID | None = None,
    ) -> bool: ...

    def list_by_company(
        self,
        company_id: UUID,
        filters: ApplicationUserFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[ApplicationUser]: ...

    def create_in_active_company(
        self,
        company_id: UUID,
        values: dict[str, Any],
        *,
        actor_id: str,
    ) -> ApplicationUser: ...

    def update(
        self,
        application_user_id: UUID,
        *,
        expected_version: int,
        values: dict[str, Any],
        actor_id: str,
    ) -> ApplicationUser: ...

    def reactivate_in_active_company(
        self,
        application_user_id: UUID,
        *,
        expected_version: int,
        actor_id: str,
    ) -> ApplicationUser: ...


class UserBranchRepository(Protocol):
    """Persistencia de asignaciones usuario–sucursal (`user_branches`)."""

    def end_read(self) -> None:
        """Cierra la transacción de lectura en curso."""

    def get_by_id(self, user_branch_id: UUID) -> UserBranch | None: ...

    def find_pair(self, application_user_id: UUID, branch_id: UUID) -> UserBranch | None: ...

    def list_all_for_user(self, application_user_id: UUID) -> list[UserBranch]: ...

    def list_by(
        self,
        *,
        application_user_id: UUID | None = None,
        branch_id: UUID | None = None,
        status: EntityStatus,
        page: int,
        page_size: int,
    ) -> PageResult[UserBranch]: ...

    def create(
        self,
        *,
        application_user_id: UUID,
        branch_id: UUID,
        company_id: UUID,
        actor_id: str,
    ) -> UserBranch: ...

    def deactivate(self, user_branch_id: UUID, *, expected_version: int, actor_id: str) -> UserBranch: ...

    def reactivate(self, user_branch_id: UUID, *, expected_version: int, actor_id: str) -> UserBranch: ...


class AdvisorAssignmentRepository(Protocol):
    """Persistencia de asignaciones de asesor (`company_advisor_assignments`)."""

    def end_read(self) -> None:
        """Cierra la transacción de lectura en curso."""

    def get_by_id(self, assignment_id: UUID) -> AdvisorAssignment | None: ...

    def find_active_primary(self, company_id: UUID) -> AdvisorAssignment | None: ...

    def exists_active_person(self, company_id: UUID, person_identity_id: UUID) -> bool: ...

    def list_by_company(
        self,
        company_id: UUID,
        filters: AdvisorFilters,
        *,
        page: int,
        page_size: int,
    ) -> PageResult[AdvisorAssignment]: ...

    def create_in_active_company(
        self,
        company_id: UUID,
        values: dict[str, Any],
        *,
        actor_id: str,
    ) -> AdvisorAssignment: ...

    def close(
        self,
        assignment_id: UUID,
        *,
        expected_version: int,
        valid_to: datetime,
        actor_id: str,
    ) -> AdvisorAssignment: ...

    def change_primary(
        self,
        company_id: UUID,
        *,
        current_assignment_id: UUID,
        expected_version: int,
        person_identity_id: UUID,
        effective_at: datetime,
        actor_id: str,
    ) -> tuple[AdvisorAssignment, AdvisorAssignment]: ...
