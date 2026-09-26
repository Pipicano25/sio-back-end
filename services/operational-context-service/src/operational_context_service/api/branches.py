"""Router HTTP de sucursales (`contracts/rest-api.md`, sección 2).

Colección y alta anidadas bajo la empresa; recurso plano por UUID para que los
consumidores solo necesiten el `branch_id` (R-04). Todas las rutas exigen
únicamente permisos de `branches`.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from operational_context_service.api.access_scope import get_access_scope
from operational_context_service.api.dependencies import get_branch_service
from operational_context_service.api.filters.branch_filters import branch_filters
from operational_context_service.api.pagination import PaginationParams
from operational_context_service.api.schemas.branch import (
    BranchCreate,
    BranchResponse,
    BranchUpdate,
)
from operational_context_service.api.schemas.common import PaginatedResponse, StatusActionRequest
from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.branch_service import BranchService
from operational_context_service.application.ports import BranchFilters

SERVICE = "operational-context"
RESOURCE = "branches"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de sucursales."""
    router = APIRouter(tags=["Sucursales"])

    @router.get(
        "/companies/{company_id}/branches",
        response_model=PaginatedResponse[BranchResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar las sucursales de una empresa",
    )
    def list_branches(
        company_id: UUID,
        pagination: PaginationParams = Depends(),
        filters: BranchFilters = Depends(branch_filters),
        scope: AccessScope = Depends(get_access_scope),
        service: BranchService = Depends(get_branch_service),
    ) -> PaginatedResponse[BranchResponse]:
        """Página de sucursales; por defecto solo `ACTIVE` (FR-023)."""
        result = service.list(
            scope,
            company_id,
            filters,
            page=pagination.page,
            page_size=pagination.page_size,
        )

        return PaginatedResponse[BranchResponse](
            items=[BranchResponse.model_validate(item) for item in result.items],
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.post(
        "/companies/{company_id}/branches",
        response_model=BranchResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Registrar una sucursal",
    )
    def create_branch(
        company_id: UUID,
        payload: BranchCreate,
        actor_id: CurrentSubject,
        response: Response,
        scope: AccessScope = Depends(get_access_scope),
        service: BranchService = Depends(get_branch_service),
    ):
        """Registra una sucursal bajo una empresa `ACTIVE` (FR-020)."""
        branch = service.create(scope, company_id, payload.model_dump(), actor_id=actor_id)
        response.headers["Location"] = f"/api/v1/branches/{branch.id}"

        return branch

    @router.get(
        "/branches/{branch_id}",
        response_model=BranchResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar una sucursal (contrato Provider)",
    )
    def get_branch(
        branch_id: UUID,
        scope: AccessScope = Depends(get_access_scope),
        service: BranchService = Depends(get_branch_service),
    ):
        """Sucursal por UUID en cualquier estado, con el estado de su empresa (FR-051)."""
        return service.get(scope, branch_id)

    @router.put(
        "/branches/{branch_id}",
        response_model=BranchResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Modificar una sucursal",
    )
    def update_branch(
        branch_id: UUID,
        payload: BranchUpdate,
        actor_id: CurrentSubject,
        scope: AccessScope = Depends(get_access_scope),
        service: BranchService = Depends(get_branch_service),
    ):
        """Reemplazo completo con versión esperada; la empresa es inmutable (FR-022)."""
        data = payload.model_dump()
        expected_version = data.pop("version")

        return service.update(
            scope,
            branch_id,
            data,
            expected_version=expected_version,
            actor_id=actor_id,
        )

    @router.post(
        "/branches/{branch_id}/deactivate",
        response_model=BranchResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "delete")],
        summary="Inactivar una sucursal (no elimina)",
    )
    def deactivate_branch(
        branch_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        scope: AccessScope = Depends(get_access_scope),
        service: BranchService = Depends(get_branch_service),
    ):
        """Inactiva sin eliminar (D7)."""
        return service.deactivate(scope, branch_id, expected_version=payload.version, actor_id=actor_id)

    @router.post(
        "/branches/{branch_id}/reactivate",
        response_model=BranchResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Reactivar una sucursal",
    )
    def reactivate_branch(
        branch_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        scope: AccessScope = Depends(get_access_scope),
        service: BranchService = Depends(get_branch_service),
    ):
        """Reactiva si su empresa está `ACTIVE` (FR-026)."""
        return service.reactivate(scope, branch_id, expected_version=payload.version, actor_id=actor_id)

    return router
