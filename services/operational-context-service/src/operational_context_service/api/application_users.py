"""Router HTTP de usuarios operativos (`contracts/rest-api.md` de la feature 005, §1).

Los errores de aplicación los traduce `api/errors.py`. Toda operación aplica el
alcance por empresa (`AccessScope`); la consulta por UUID admite además la
capacidad `platform:lookup` (FR-045).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from operational_context_service.api.access_scope import get_access_scope
from operational_context_service.api.dependencies import get_application_user_service
from operational_context_service.api.filters.application_user_filters import (
    application_user_filters,
)
from operational_context_service.api.pagination import PaginationParams
from operational_context_service.api.schemas.application_user import (
    ApplicationUserCreate,
    ApplicationUserResponse,
    ApplicationUserUpdate,
)
from operational_context_service.api.schemas.common import PaginatedResponse, StatusActionRequest
from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.application_user_service import ApplicationUserService
from operational_context_service.application.ports import ApplicationUserFilters

SERVICE = "operational-context"
RESOURCE = "application_users"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de usuarios operativos."""
    router = APIRouter(tags=["Usuarios operativos"])

    @router.get(
        "/companies/{company_id}/application-users",
        response_model=PaginatedResponse[ApplicationUserResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar los usuarios operativos de una empresa",
    )
    def list_application_users(
        company_id: UUID,
        pagination: PaginationParams = Depends(),
        filters: ApplicationUserFilters = Depends(application_user_filters),
        scope: AccessScope = Depends(get_access_scope),
        service: ApplicationUserService = Depends(get_application_user_service),
    ) -> PaginatedResponse[ApplicationUserResponse]:
        """Página de membresías; por defecto solo `ACTIVE` (FR-015)."""
        result = service.list(scope, company_id, filters, page=pagination.page, page_size=pagination.page_size)

        return PaginatedResponse[ApplicationUserResponse](
            items=[ApplicationUserResponse.model_validate(item) for item in result.items],
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.post(
        "/companies/{company_id}/application-users",
        response_model=ApplicationUserResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Registrar un usuario operativo en una empresa",
    )
    def create_application_user(
        company_id: UUID,
        payload: ApplicationUserCreate,
        actor_id: CurrentSubject,
        response: Response,
        scope: AccessScope = Depends(get_access_scope),
        service: ApplicationUserService = Depends(get_application_user_service),
    ):
        """Membresía de una persona humana validada en Keycloak y Party Identity (FR-010 a FR-019)."""
        user = service.create(scope, company_id, payload.model_dump(), actor_id=actor_id)
        response.headers["Location"] = f"/api/v1/application-users/{user.id}"

        return user

    @router.get(
        "/application-users/{application_user_id}",
        response_model=ApplicationUserResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar un usuario operativo (contrato Provider)",
    )
    def get_application_user(
        application_user_id: UUID,
        scope: AccessScope = Depends(get_access_scope),
        service: ApplicationUserService = Depends(get_application_user_service),
    ):
        """Membresía por UUID en cualquier estado (FR-072)."""
        return service.get(scope, application_user_id)

    @router.put(
        "/application-users/{application_user_id}",
        response_model=ApplicationUserResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Modificar los datos de referencia de un usuario operativo",
    )
    def update_application_user(
        application_user_id: UUID,
        payload: ApplicationUserUpdate,
        actor_id: CurrentSubject,
        scope: AccessScope = Depends(get_access_scope),
        service: ApplicationUserService = Depends(get_application_user_service),
    ):
        """Solo nombre y correo de referencia; `sub`, persona y empresa son inmutables (FR-013)."""
        return service.update(
            scope,
            application_user_id,
            payload.model_dump(include={"display_name", "reference_email"}),
            expected_version=payload.version,
            actor_id=actor_id,
        )

    @router.post(
        "/application-users/{application_user_id}/deactivate",
        response_model=ApplicationUserResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "delete")],
        summary="Inactivar un usuario operativo (no elimina)",
    )
    def deactivate_application_user(
        application_user_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        scope: AccessScope = Depends(get_access_scope),
        service: ApplicationUserService = Depends(get_application_user_service),
    ):
        """Inactiva solo esta membresía (FR-014, DS-11)."""
        return service.deactivate(scope, application_user_id, expected_version=payload.version, actor_id=actor_id)

    @router.post(
        "/application-users/{application_user_id}/reactivate",
        response_model=ApplicationUserResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Reactivar un usuario operativo",
    )
    def reactivate_application_user(
        application_user_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        scope: AccessScope = Depends(get_access_scope),
        service: ApplicationUserService = Depends(get_application_user_service),
    ):
        """Reactiva revalidando cuenta y persona (FR-014, R-14)."""
        return service.reactivate(scope, application_user_id, expected_version=payload.version, actor_id=actor_id)

    return router
