"""Servicios de sectores económicos y de sus asignaciones (FR-050–FR-065, DS-08, DS-09, DS-12)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from party_identity_service.application.exceptions import (
    DomainValidationError,
    ImmutableFieldError,
    InvalidSectorHierarchyError,
    InvalidStatusTransitionError,
    NotFoundError,
    OrganizationIdentityInactiveError,
    SectorHasActiveChildrenError,
    SectorInactiveError,
    VersionConflictError,
)
from party_identity_service.application.pagination import PageResult
from party_identity_service.application.ports import (
    BusinessSectorRepository,
    OrganizationBusinessSectorRepository,
    OrganizationIdentityRepository,
)
from party_identity_service.domain.business_sector import (
    BusinessSector,
    OrganizationBusinessSector,
    SectorStatus,
    normalize_code,
)
from party_identity_service.domain.contact import RelationState, normalize_optional_text


class BusinessSectorService:
    """Catálogo global y jerárquico de sectores."""

    def __init__(self, *, sectors: BusinessSectorRepository) -> None:
        self.sectors = sectors

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
    ) -> PageResult[BusinessSector]:
        return self.sectors.list_all(
            page=page,
            page_size=page_size,
            classification_system=normalize_code(classification_system) if classification_system else None,
            code=normalize_code(code) if code else None,
            parent_sector_id=parent_sector_id,
            roots_only=roots_only,
            status=status,
            search=normalize_optional_text(search),
        )

    def get(self, sector_id: UUID) -> BusinessSector:
        sector = self.sectors.get_by_id(sector_id)
        if sector is None:
            raise NotFoundError("El sector no existe.")
        return sector

    def create(
        self,
        *,
        classification_system: str,
        code: str,
        name: str,
        description: str | None,
        parent_sector_id: UUID | None,
        actor_id: str,
    ) -> BusinessSector:
        system = normalize_code(classification_system)
        if parent_sector_id is not None:
            self._check_parent(parent_sector_id, system)
        return self.sectors.create(
            parent_sector_id=parent_sector_id,
            classification_system=system,
            code=normalize_code(code),
            name=name.strip(),
            description=normalize_optional_text(description),
            actor_id=actor_id,
        )

    def update(
        self,
        sector_id: UUID,
        *,
        expected_version: int,
        name: str,
        description: str | None,
        parent_sector_id: UUID | None,
        actor_id: str,
        immutable_fields: list[str] | None = None,
    ) -> BusinessSector:
        if immutable_fields:
            raise ImmutableFieldError(
                "classification_system y code identifican al sector y no se modifican: "
                + ", ".join(immutable_fields)
            )
        current = self.get(sector_id)
        if current.version != expected_version:
            raise VersionConflictError

        values = {
            "name": name.strip(),
            "description": normalize_optional_text(description),
            "parent_sector_id": parent_sector_id,
        }
        if all(getattr(current, field) == value for field, value in values.items()):
            return current

        if parent_sector_id is not None and parent_sector_id != current.parent_sector_id:
            self._check_parent(parent_sector_id, current.classification_system)
            if sector_id in self.sectors.ancestor_ids(parent_sector_id):
                raise InvalidSectorHierarchyError("El sector superior no puede ser un descendiente (ciclo).")

        return self.sectors.update(sector_id, expected_version=expected_version, values=values, actor_id=actor_id)

    def deactivate(self, sector_id: UUID, *, expected_version: int, actor_id: str) -> BusinessSector:
        current = self.get(sector_id)
        if current.version != expected_version:
            raise VersionConflictError
        if current.status != "ACTIVE":
            raise InvalidStatusTransitionError("El sector ya está inactivo.")
        if self.sectors.has_active_children(sector_id):
            raise SectorHasActiveChildrenError
        return self.sectors.update(
            sector_id, expected_version=expected_version, values={"status": "INACTIVE"}, actor_id=actor_id
        )

    def reactivate(self, sector_id: UUID, *, expected_version: int, actor_id: str) -> BusinessSector:
        current = self.get(sector_id)
        if current.version != expected_version:
            raise VersionConflictError
        if current.status != "INACTIVE":
            raise InvalidStatusTransitionError("El sector ya está activo.")
        if current.parent_sector_id is not None:
            parent = self.sectors.get_by_id(current.parent_sector_id)
            if parent is None or parent.status != "ACTIVE":
                raise InvalidSectorHierarchyError("El sector superior está inactivo.")
        return self.sectors.update(
            sector_id, expected_version=expected_version, values={"status": "ACTIVE"}, actor_id=actor_id
        )

    def _check_parent(self, parent_sector_id: UUID, classification_system: str) -> None:
        parent = self.sectors.get_by_id(parent_sector_id)
        if parent is None:
            raise InvalidSectorHierarchyError("El sector superior no existe.")
        if parent.status != "ACTIVE":
            raise InvalidSectorHierarchyError("El sector superior está inactivo.")
        if parent.classification_system != classification_system:
            raise InvalidSectorHierarchyError("El sector superior pertenece a otro sistema de clasificación.")


class OrganizationBusinessSectorService:
    """Sectores de una organización con vigencia `[valid_from, valid_to)`."""

    def __init__(
        self,
        *,
        assignments: OrganizationBusinessSectorRepository,
        sectors: BusinessSectorRepository,
        organizations: OrganizationIdentityRepository,
    ) -> None:
        self.assignments = assignments
        self.sectors = sectors
        self.organizations = organizations

    def list_by_organization(
        self, organization_id: UUID, *, state: RelationState, page: int, page_size: int
    ) -> PageResult[OrganizationBusinessSector]:
        self._organization(organization_id)
        return self.assignments.list_by_organization(organization_id, state=state, page=page, page_size=page_size)

    def get(self, assignment_id: UUID) -> OrganizationBusinessSector:
        assignment = self.assignments.get_by_id(assignment_id)
        if assignment is None:
            raise NotFoundError("La asignación de sector no existe.")
        return assignment

    def assign(
        self,
        organization_id: UUID,
        *,
        global_business_sector_id: UUID,
        is_primary: bool,
        valid_from: datetime | None,
        actor_id: str,
    ) -> OrganizationBusinessSector:
        organization = self._organization(organization_id)
        if organization.status != "ACTIVE":
            raise OrganizationIdentityInactiveError
        sector = self.sectors.get_by_id(global_business_sector_id)
        if sector is None:
            raise DomainValidationError("global_business_sector_id", "El sector indicado no existe.")
        if sector.status != "ACTIVE":
            raise SectorInactiveError
        return self.assignments.create(
            organization_id=organization_id,
            sector_id=global_business_sector_id,
            is_primary=is_primary,
            valid_from=valid_from,
            actor_id=actor_id,
        )

    def set_primary(self, assignment_id: UUID, *, expected_version: int, actor_id: str) -> OrganizationBusinessSector:
        """Establece el sector principal de forma atómica (DS-12, FR-063)."""
        return self.assignments.set_primary(assignment_id, expected_version=expected_version, actor_id=actor_id)

    def close(self, assignment_id: UUID, *, expected_version: int, actor_id: str) -> OrganizationBusinessSector:
        """Cierra sin reactivación posible (DS-08)."""
        return self.assignments.close(assignment_id, expected_version=expected_version, actor_id=actor_id)

    def _organization(self, organization_id: UUID):
        organization = self.organizations.get_by_id(organization_id)
        if organization is None:
            raise NotFoundError("La organización solicitada no existe.")
        return organization
