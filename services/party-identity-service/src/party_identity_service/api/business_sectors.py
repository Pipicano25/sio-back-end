"""Routers HTTP de sectores económicos y de sectores de organización (§3 y §4)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sio_auth import CurrentSubject, SIOAuth

from party_identity_service.api.dependencies import (
    get_business_sector_service,
    get_organization_business_sector_service,
)
from party_identity_service.api.pagination import PaginationParams
from party_identity_service.api.schemas.business_sector import (
    BusinessSectorCreate,
    BusinessSectorResponse,
    BusinessSectorUpdate,
    OrganizationBusinessSectorCreate,
    OrganizationBusinessSectorResponse,
)
from party_identity_service.api.schemas.contact_person import VersionRequest
from party_identity_service.api.schemas.pagination import PaginatedResponse
from party_identity_service.application.business_sector_service import (
    BusinessSectorService,
    OrganizationBusinessSectorService,
)

SERVICE = "party-identity"
SECTORS = "global_business_sectors"
ASSIGNMENTS = "organization_business_sectors"

StateParam = Literal["active", "closed", "all"]


def _page(result) -> PaginatedResponse:
    return PaginatedResponse(
        items=result.items,
        page=result.page,
        page_size=result.page_size,
        total_records=result.total_records,
        total_pages=result.total_pages,
    )


def build_sectors_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(prefix="/global-business-sectors", tags=["Sectores económicos"])

    @router.get(
        "",
        response_model=PaginatedResponse[BusinessSectorResponse],
        dependencies=[auth.permission(SERVICE, SECTORS, "read")],
        summary="Consultar sectores económicos",
    )
    def list_sectors(
        classification_system: str | None = Query(default=None, max_length=30),
        code: str | None = Query(default=None, max_length=40),
        parent_sector_id: UUID | None = None,
        level_root: bool = Query(default=False, description="Solo sectores sin padre."),
        status_filter: Literal["ACTIVE", "INACTIVE"] = Query(default="ACTIVE", alias="status"),
        search: str | None = Query(default=None, max_length=255),
        pagination: PaginationParams = Depends(),
        service: BusinessSectorService = Depends(get_business_sector_service),
    ):
        return _page(
            service.list_all(
                page=pagination.page,
                page_size=pagination.page_size,
                classification_system=classification_system,
                code=code,
                parent_sector_id=parent_sector_id,
                roots_only=level_root,
                status=status_filter,
                search=search,
            )
        )

    @router.get(
        "/{sector_id}",
        response_model=BusinessSectorResponse,
        dependencies=[auth.permission(SERVICE, SECTORS, "read")],
        summary="Consultar un sector por UUID",
    )
    def get_sector(sector_id: UUID, service: BusinessSectorService = Depends(get_business_sector_service)):
        return service.get(sector_id)

    @router.post(
        "",
        response_model=BusinessSectorResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, SECTORS, "create")],
        summary="Crear un sector",
    )
    def create_sector(
        payload: BusinessSectorCreate,
        actor_id: CurrentSubject,
        service: BusinessSectorService = Depends(get_business_sector_service),
    ):
        return service.create(**payload.model_dump(), actor_id=actor_id)

    @router.put(
        "/{sector_id}",
        response_model=BusinessSectorResponse,
        dependencies=[auth.permission(SERVICE, SECTORS, "update")],
        summary="Modificar nombre, descripción o sector superior",
    )
    def update_sector(
        sector_id: UUID,
        payload: BusinessSectorUpdate,
        actor_id: CurrentSubject,
        service: BusinessSectorService = Depends(get_business_sector_service),
    ):
        immutable = [name for name in ("classification_system", "code") if getattr(payload, name) is not None]
        return service.update(
            sector_id,
            expected_version=payload.version,
            name=payload.name,
            description=payload.description,
            parent_sector_id=payload.parent_sector_id,
            actor_id=actor_id,
            immutable_fields=immutable,
        )

    @router.post(
        "/{sector_id}:deactivate",
        response_model=BusinessSectorResponse,
        dependencies=[auth.permission(SERVICE, SECTORS, "delete")],
        summary="Inactivar un sector (no elimina; sin cascada)",
    )
    def deactivate_sector(
        sector_id: UUID,
        payload: VersionRequest,
        actor_id: CurrentSubject,
        service: BusinessSectorService = Depends(get_business_sector_service),
    ):
        return service.deactivate(sector_id, expected_version=payload.version, actor_id=actor_id)

    @router.post(
        "/{sector_id}:reactivate",
        response_model=BusinessSectorResponse,
        dependencies=[auth.permission(SERVICE, SECTORS, "update")],
        summary="Reactivar un sector",
    )
    def reactivate_sector(
        sector_id: UUID,
        payload: VersionRequest,
        actor_id: CurrentSubject,
        service: BusinessSectorService = Depends(get_business_sector_service),
    ):
        return service.reactivate(sector_id, expected_version=payload.version, actor_id=actor_id)

    return router


def build_organization_sectors_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=["Sectores de organización"])
    collection = "/organization-identities/{organization_identity_id}/business-sectors"
    item = "/organization-business-sectors/{assignment_id}"

    @router.get(
        collection,
        response_model=PaginatedResponse[OrganizationBusinessSectorResponse],
        dependencies=[auth.permission(SERVICE, ASSIGNMENTS, "read")],
        summary="Consultar los sectores de una organización (contrato Provider)",
    )
    def list_assignments(
        organization_identity_id: UUID,
        state: StateParam = Query(default="active", description="active (vigentes), closed (cerradas) o all."),
        pagination: PaginationParams = Depends(),
        service: OrganizationBusinessSectorService = Depends(get_organization_business_sector_service),
    ):
        return _page(
            service.list_by_organization(
                organization_identity_id, state=state, page=pagination.page, page_size=pagination.page_size
            )
        )

    @router.post(
        collection,
        response_model=OrganizationBusinessSectorResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, ASSIGNMENTS, "create")],
        summary="Asignar un sector a una organización",
    )
    def assign(
        organization_identity_id: UUID,
        payload: OrganizationBusinessSectorCreate,
        actor_id: CurrentSubject,
        service: OrganizationBusinessSectorService = Depends(get_organization_business_sector_service),
    ):
        return service.assign(organization_identity_id, **payload.model_dump(), actor_id=actor_id)

    @router.get(
        item,
        response_model=OrganizationBusinessSectorResponse,
        dependencies=[auth.permission(SERVICE, ASSIGNMENTS, "read")],
        summary="Consultar una asignación de sector por UUID",
    )
    def get_assignment(
        assignment_id: UUID,
        service: OrganizationBusinessSectorService = Depends(get_organization_business_sector_service),
    ):
        return service.get(assignment_id)

    @router.post(
        f"{item}:set-primary",
        response_model=OrganizationBusinessSectorResponse,
        dependencies=[auth.permission(SERVICE, ASSIGNMENTS, "update")],
        summary="Establecer el sector principal (atómico)",
    )
    def set_primary(
        assignment_id: UUID,
        payload: VersionRequest,
        actor_id: CurrentSubject,
        service: OrganizationBusinessSectorService = Depends(get_organization_business_sector_service),
    ):
        return service.set_primary(assignment_id, expected_version=payload.version, actor_id=actor_id)

    @router.post(
        f"{item}:close",
        response_model=OrganizationBusinessSectorResponse,
        dependencies=[auth.permission(SERVICE, ASSIGNMENTS, "delete")],
        summary="Cerrar una asignación de sector (no se reactiva)",
    )
    def close(
        assignment_id: UUID,
        payload: VersionRequest,
        actor_id: CurrentSubject,
        service: OrganizationBusinessSectorService = Depends(get_organization_business_sector_service),
    ):
        return service.close(assignment_id, expected_version=payload.version, actor_id=actor_id)

    return router
