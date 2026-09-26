"""Router HTTP de asesores (`contracts/rest-api.md` de la feature 005, §3).

No hay `PUT` ni reactivación: una asignación cerrada es inmutable (DS-13).
`change-primary` exige `create` **y** `delete` de `company_advisor_assignments`.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from operational_context_service.api.access_scope import get_access_scope
from operational_context_service.api.dependencies import get_advisor_assignment_service
from operational_context_service.api.filters.advisor_filters import advisor_filters
from operational_context_service.api.pagination import PaginationParams
from operational_context_service.api.schemas.advisor_assignment import (
    AdvisorAssignmentCreate,
    AdvisorAssignmentResponse,
    AdvisorCloseRequest,
    ChangePrimaryRequest,
    ChangePrimaryResponse,
)
from operational_context_service.api.schemas.common import PaginatedResponse
from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.advisor_assignment_service import (
    AdvisorAssignmentService,
)
from operational_context_service.application.ports import AdvisorFilters

SERVICE = "operational-context"
RESOURCE = "company_advisor_assignments"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de asesores."""
    router = APIRouter(tags=["Asesores"])

    @router.get(
        "/companies/{company_id}/advisor-assignments",
        response_model=PaginatedResponse[AdvisorAssignmentResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar el historial de asesores de una empresa",
    )
    def list_advisors(
        company_id: UUID,
        pagination: PaginationParams = Depends(),
        filters: AdvisorFilters = Depends(advisor_filters),
        scope: AccessScope = Depends(get_access_scope),
        service: AdvisorAssignmentService = Depends(get_advisor_assignment_service),
    ):
        result = service.list(scope, company_id, filters, page=pagination.page, page_size=pagination.page_size)

        return PaginatedResponse[AdvisorAssignmentResponse](
            items=[AdvisorAssignmentResponse.model_validate(item) for item in result.items],
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.post(
        "/companies/{company_id}/advisor-assignments",
        response_model=AdvisorAssignmentResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Registrar un asesor de la empresa",
    )
    def create_advisor(
        company_id: UUID,
        payload: AdvisorAssignmentCreate,
        actor_id: CurrentSubject,
        response: Response,
        scope: AccessScope = Depends(get_access_scope),
        service: AdvisorAssignmentService = Depends(get_advisor_assignment_service),
    ):
        assignment = service.create(
            scope,
            company_id,
            person_identity_id=payload.person_identity_id,
            is_primary=payload.is_primary,
            valid_from=payload.valid_from,
            actor_id=actor_id,
        )
        response.headers["Location"] = f"/api/v1/advisor-assignments/{assignment.id}"

        return assignment

    @router.get(
        "/advisor-assignments/{assignment_id}",
        response_model=AdvisorAssignmentResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar una asignación de asesor",
    )
    def get_advisor(
        assignment_id: UUID,
        scope: AccessScope = Depends(get_access_scope),
        service: AdvisorAssignmentService = Depends(get_advisor_assignment_service),
    ):
        return service.get(scope, assignment_id)

    @router.post(
        "/advisor-assignments/{assignment_id}/close",
        response_model=AdvisorAssignmentResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "delete")],
        summary="Cerrar una asignación de asesor (no elimina)",
    )
    def close_advisor(
        assignment_id: UUID,
        payload: AdvisorCloseRequest,
        actor_id: CurrentSubject,
        scope: AccessScope = Depends(get_access_scope),
        service: AdvisorAssignmentService = Depends(get_advisor_assignment_service),
    ):
        return service.close(
            scope,
            assignment_id,
            expected_version=payload.version,
            valid_to=payload.valid_to,
            actor_id=actor_id,
        )

    @router.post(
        "/companies/{company_id}/advisor-assignments/change-primary",
        response_model=ChangePrimaryResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            auth.permission(SERVICE, RESOURCE, "create"),
            auth.permission(SERVICE, RESOURCE, "delete"),
        ],
        summary="Cambiar el asesor principal (cierra la vigente y crea la nueva)",
    )
    def change_primary(
        company_id: UUID,
        payload: ChangePrimaryRequest,
        actor_id: CurrentSubject,
        scope: AccessScope = Depends(get_access_scope),
        service: AdvisorAssignmentService = Depends(get_advisor_assignment_service),
    ):
        closed, created = service.change_primary(
            scope,
            company_id,
            current_assignment_id=payload.current_assignment_id,
            expected_version=payload.version,
            person_identity_id=payload.person_identity_id,
            effective_at=payload.effective_at,
            actor_id=actor_id,
        )

        return ChangePrimaryResponse(
            closed=AdvisorAssignmentResponse.model_validate(closed),
            created=AdvisorAssignmentResponse.model_validate(created),
        )

    return router
