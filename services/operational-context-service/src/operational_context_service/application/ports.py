"""Puertos de la capa de aplicación (Principio XV, R-06).

Cada integración con otro microservicio se consume detrás de un puerto; el
adaptador HTTP real vive en `infrastructure/` y las pruebas inyectan dobles.
Los registros devueltos por los proveedores se usan solo en memoria y nunca se
persisten (FR-044).
"""

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from operational_context_service.application.pagination import PageResult
from operational_context_service.domain.entities import Branch, Company
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

