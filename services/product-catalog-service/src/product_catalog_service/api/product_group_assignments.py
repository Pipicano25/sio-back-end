"""Router de grupos del producto (`contracts/rest-api.md` §6.6)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from product_catalog_service.api.schemas.base import STATUS_PATTERN, VersionRequest
from product_catalog_service.api.schemas.dependents import GroupAssignmentResponse
from product_catalog_service.api.schemas.group import GroupAssignmentCreate
from product_catalog_service.api.security import permission
from product_catalog_service.application.group_assignment_service import GroupAssignmentService
from product_catalog_service.infrastructure.database import get_db_session

RESOURCE = "products"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de asignaciones de grupo."""
    router = APIRouter(prefix="/products/{product_id}/group-assignments", tags=["Productos: grupos"])

    def get_service(session: Session = Depends(get_db_session)) -> GroupAssignmentService:
        return GroupAssignmentService(session)

    @router.get(
        "",
        response_model=list[GroupAssignmentResponse],
        dependencies=[permission(auth, RESOURCE, "read")],
        summary="Listar los grupos del producto",
    )
    def list_assignments(
        product_id: UUID,
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        service: GroupAssignmentService = Depends(get_service),
    ):
        return [GroupAssignmentResponse.model_validate(item) for item in service.list(product_id, status_filter)]

    @router.post(
        "",
        response_model=GroupAssignmentResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission(auth, RESOURCE, "update")],
        summary="Asignar un grupo al producto",
    )
    def assign_group(
        product_id: UUID,
        body: GroupAssignmentCreate,
        response: Response,
        actor: CurrentSubject,
        service: GroupAssignmentService = Depends(get_service),
    ):
        assignment, created = service.assign(product_id, body.global_product_group_id, actor)
        if not created:
            response.status_code = status.HTTP_200_OK
        return GroupAssignmentResponse.model_validate(assignment)

    @router.post(
        "/{assignment_id}/deactivate",
        response_model=GroupAssignmentResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Retirar un grupo del producto",
    )
    def deactivate_assignment(
        product_id: UUID,
        assignment_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: GroupAssignmentService = Depends(get_service),
    ):
        return GroupAssignmentResponse.model_validate(
            service.deactivate(product_id, assignment_id, version=body.version, actor=actor)
        )

    @router.post(
        "/{assignment_id}/reactivate",
        response_model=GroupAssignmentResponse,
        dependencies=[permission(auth, RESOURCE, "deactivate")],
        summary="Reactivar un grupo del producto",
    )
    def reactivate_assignment(
        product_id: UUID,
        assignment_id: UUID,
        body: VersionRequest,
        actor: CurrentSubject,
        service: GroupAssignmentService = Depends(get_service),
    ):
        return GroupAssignmentResponse.model_validate(
            service.reactivate(product_id, assignment_id, version=body.version, actor=actor)
        )

    return router
