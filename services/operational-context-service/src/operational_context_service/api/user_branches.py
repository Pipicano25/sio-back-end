"""Router HTTP de asignaciones usuario–sucursal (`contracts/rest-api.md` de la feature 005, §2).

No hay `PUT`: usuario y sucursal son inmutables y el resto de campos los
gestiona el servicio. No hay `DELETE` (D7).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth

from operational_context_service.api.access_scope import get_access_scope
from operational_context_service.api.dependencies import get_user_branch_service
from operational_context_service.api.pagination import PaginationParams
from operational_context_service.api.schemas.common import PaginatedResponse, StatusActionRequest
from operational_context_service.api.schemas.user_branch import (
    OperationalAccessSummary,
    UserBranchCreate,
    UserBranchResponse,
)
from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.pagination import PageResult
from operational_context_service.application.user_branch_service import (
    UserBranchService,
    assignment_access,
)
from operational_context_service.domain.entities import UserBranch
from operational_context_service.domain.status import EntityStatus

SERVICE = "operational-context"
RESOURCE = "user_branches"


def to_response(user_branch: UserBranch) -> UserBranchResponse:
    """Respuesta con el acceso operativo calculado (sin permiso concreto)."""
    allowed, reason = assignment_access(user_branch)

    return UserBranchResponse(
        id=user_branch.id,
        application_user_id=user_branch.application_user_id,
        branch_id=user_branch.branch_id,
        company_id=user_branch.company_id,
        status=user_branch.status,
        assigned_at=user_branch.assigned_at,
        assigned_by=user_branch.assigned_by,
        deactivated_at=user_branch.deactivated_at,
        membership_status=user_branch.membership_status,
        branch_status=user_branch.branch_status,
        company_status=user_branch.company_status,
        operational_access=OperationalAccessSummary(allowed=allowed, reason=reason),
        version=user_branch.version,
        created_by=user_branch.created_by,
        updated_by=user_branch.updated_by,
        created_at=user_branch.created_at,
        updated_at=user_branch.updated_at,
    )


def _page(result: PageResult[UserBranch]) -> PaginatedResponse[UserBranchResponse]:
    return PaginatedResponse[UserBranchResponse](
        items=[to_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total_records=result.total_records,
        total_pages=result.total_pages,
    )


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de asignaciones usuario–sucursal."""
    router = APIRouter(tags=["Asignaciones a sucursales"])

    @router.get(
        "/application-users/{application_user_id}/user-branches",
        response_model=PaginatedResponse[UserBranchResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar las sucursales asignadas a un usuario operativo",
    )
    def list_by_user(
        application_user_id: UUID,
        status_filter: EntityStatus = Query(default="ACTIVE", alias="status"),
        pagination: PaginationParams = Depends(),
        scope: AccessScope = Depends(get_access_scope),
        service: UserBranchService = Depends(get_user_branch_service),
    ):
        return _page(
            service.list_by_user(
                scope,
                application_user_id,
                status_filter,
                page=pagination.page,
                page_size=pagination.page_size,
            )
        )

    @router.get(
        "/branches/{branch_id}/user-branches",
        response_model=PaginatedResponse[UserBranchResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar los usuarios asignados a una sucursal",
    )
    def list_by_branch(
        branch_id: UUID,
        status_filter: EntityStatus = Query(default="ACTIVE", alias="status"),
        pagination: PaginationParams = Depends(),
        scope: AccessScope = Depends(get_access_scope),
        service: UserBranchService = Depends(get_user_branch_service),
    ):
        return _page(
            service.list_by_branch(
                scope,
                branch_id,
                status_filter,
                page=pagination.page,
                page_size=pagination.page_size,
            )
        )

    @router.post(
        "/application-users/{application_user_id}/user-branches",
        response_model=UserBranchResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Asignar una sucursal a un usuario operativo",
    )
    def create_user_branch(
        application_user_id: UUID,
        payload: UserBranchCreate,
        actor_id: CurrentSubject,
        response: Response,
        scope: AccessScope = Depends(get_access_scope),
        service: UserBranchService = Depends(get_user_branch_service),
    ):
        user_branch = service.create(scope, application_user_id, payload.branch_id, actor_id=actor_id)
        response.headers["Location"] = f"/api/v1/user-branches/{user_branch.id}"

        return to_response(user_branch)

    @router.get(
        "/user-branches/{user_branch_id}",
        response_model=UserBranchResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar una asignación",
    )
    def get_user_branch(
        user_branch_id: UUID,
        scope: AccessScope = Depends(get_access_scope),
        service: UserBranchService = Depends(get_user_branch_service),
    ):
        return to_response(service.get(scope, user_branch_id))

    @router.post(
        "/user-branches/{user_branch_id}/deactivate",
        response_model=UserBranchResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "delete")],
        summary="Retirar una asignación (no elimina)",
    )
    def deactivate_user_branch(
        user_branch_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        scope: AccessScope = Depends(get_access_scope),
        service: UserBranchService = Depends(get_user_branch_service),
    ):
        return to_response(
            service.deactivate(scope, user_branch_id, expected_version=payload.version, actor_id=actor_id)
        )

    @router.post(
        "/user-branches/{user_branch_id}/reactivate",
        response_model=UserBranchResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Reactivar una asignación",
    )
    def reactivate_user_branch(
        user_branch_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        scope: AccessScope = Depends(get_access_scope),
        service: UserBranchService = Depends(get_user_branch_service),
    ):
        return to_response(
            service.reactivate(scope, user_branch_id, expected_version=payload.version, actor_id=actor_id)
        )

    return router
