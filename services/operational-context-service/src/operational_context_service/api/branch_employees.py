"""Router HTTP de empleados por sucursal (FR-025a de la feature 005).

Solo lectura: exige los permisos de lectura de asignaciones, sucursales y
usuarios operativos, y membresía en la empresa (o `platform:administer`).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sio_auth import SIOAuth

from operational_context_service.api.access_scope import get_access_scope
from operational_context_service.api.dependencies import get_branch_employees_service
from operational_context_service.api.pagination import PaginationParams
from operational_context_service.api.schemas.branch_employees import BranchEmployeesResponse
from operational_context_service.api.schemas.common import PaginatedResponse
from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.branch_employees_service import BranchEmployeesService
from operational_context_service.domain.status import EntityStatus

SERVICE = "operational-context"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de empleados por sucursal."""
    router = APIRouter(tags=["Asignaciones a sucursales"])

    @router.get(
        "/companies/{company_id}/branch-employees",
        response_model=PaginatedResponse[BranchEmployeesResponse],
        dependencies=[
            auth.permission(SERVICE, "user_branches", "read"),
            auth.permission(SERVICE, "branches", "read"),
            auth.permission(SERVICE, "application_users", "read"),
        ],
        summary="Consultar los empleados de una empresa separados por sucursal",
    )
    def list_branch_employees(
        company_id: UUID,
        branch_id: UUID | None = Query(default=None, description="Solo esta sucursal, en cualquier estado."),
        status_filter: EntityStatus = Query(
            default="ACTIVE",
            alias="status",
            description="Estado de las sucursales; por defecto solo ACTIVE.",
        ),
        assignment_status: EntityStatus = Query(
            default="ACTIVE",
            description="Estado de las asignaciones; por defecto solo ACTIVE.",
        ),
        search: str | None = Query(
            default=None,
            max_length=160,
            description="Búsqueda parcial, sin distinguir mayúsculas, en el código y el nombre de la sucursal.",
        ),
        pagination: PaginationParams = Depends(),
        scope: AccessScope = Depends(get_access_scope),
        service: BranchEmployeesService = Depends(get_branch_employees_service),
    ) -> PaginatedResponse[BranchEmployeesResponse]:
        """Página de sucursales (código y nombre) con sus empleados; la paginación es de sucursales."""
        cleaned = search.strip() if search else None
        result = service.list(
            scope,
            company_id,
            branch_id=branch_id,
            branch_status=status_filter,
            assignment_status=assignment_status,
            search=cleaned or None,
            page=pagination.page,
            page_size=pagination.page_size,
        )

        return PaginatedResponse[BranchEmployeesResponse](
            items=[BranchEmployeesResponse.of(group) for group in result.items],
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    return router
