"""Router de los contratos Provider de acceso operativo (US4; `operational-access-provider.md`).

Una denegación correctamente evaluada responde `200` con `allowed: false` y
una causa estable (DS-08); `4xx`/`5xx` quedan para errores de contrato, de
autenticación o autorización del consumidor y de indisponibilidad técnica.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sio_auth import SIOAuth

from operational_context_service.api.access_scope import get_access_scope
from operational_context_service.api.dependencies import get_operational_access_service
from operational_context_service.api.schemas.access import (
    MeOperationalContextResponse,
    OperationalAccessResponse,
)
from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.operational_access_service import (
    OperationalAccessService,
)

SERVICE = "operational-context"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de contexto y acceso operativo."""
    router = APIRouter(tags=["Acceso operativo"])

    @router.get(
        "/me/operational-context",
        response_model=MeOperationalContextResponse,
        dependencies=[auth.permission(SERVICE, "application_users", "read")],
        summary="Consultar el contexto operativo propio",
    )
    def get_my_operational_context(
        scope: AccessScope = Depends(get_access_scope),
        service: OperationalAccessService = Depends(get_operational_access_service),
    ):
        """Membresías del usuario autenticado y sus sucursales con acceso efectivo (FR-070)."""
        return MeOperationalContextResponse(
            keycloak_user_id=scope.subject,
            memberships=service.me(scope),
        )

    @router.get(
        "/operational-access",
        response_model=OperationalAccessResponse,
        dependencies=[auth.permission(SERVICE, "application_users", "read")],
        summary="Comprobar el acceso operativo a una empresa o sucursal",
    )
    def check_operational_access(
        branch_id: UUID | None = Query(default=None),
        company_id: UUID | None = Query(default=None),
        permission: str | None = Query(
            default=None,
            max_length=255,
            description="Permiso concreto que exige la operación: perm:{servicio}:{recurso}:{accion}.",
        ),
        keycloak_user_id: str | None = Query(
            default=None,
            max_length=255,
            description="Solo con perm:operational-context:platform:lookup: evalúa a otro usuario.",
        ),
        scope: AccessScope = Depends(get_access_scope),
        service: OperationalAccessService = Depends(get_operational_access_service),
    ):
        """Resultado `allowed` y causa estable; nunca `403` por una denegación funcional (FR-071)."""
        return service.check(
            scope,
            company_id=company_id,
            branch_id=branch_id,
            permission=permission,
            keycloak_user_id=keycloak_user_id,
        )

    return router
