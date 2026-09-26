"""Router HTTP para identidades globales de organizaciones.

Los errores de aplicación los traduce `api/errors.py`; este módulo no asigna
estados HTTP de error.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from party_identity_service.api.dependencies import (
    get_organization_identity_service,
)
from party_identity_service.api.filters.organization_identity import (
    OrganizationIdentityFilters,
)
from party_identity_service.api.pagination import PaginationParams
from party_identity_service.api.schemas.organization_identity import (
    OrganizationIdentityCreate,
    OrganizationIdentityResponse,
    OrganizationIdentityUpdate,
)
from party_identity_service.api.schemas.pagination import PaginatedResponse
from party_identity_service.api.schemas.status_action import StatusActionRequest
from party_identity_service.application.organization_identity_service import (
    OrganizationIdentityService,
)

SERVICE = "party-identity"
RESOURCE = "organization_identities"
BASE_PATH = "/organization-identities"


def build_router(
    auth: SIOAuth,
) -> APIRouter:
    """Construye el router de identidades de organizaciones."""
    router = APIRouter(
        prefix=BASE_PATH,
        tags=["Identidades de organizaciones"],
    )

    @router.get(
        "",
        response_model=PaginatedResponse[OrganizationIdentityResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar identidades de organizaciones",
    )
    def list_organization_identities(
        pagination: PaginationParams = Depends(),
        filters: OrganizationIdentityFilters = Depends(),
        service: OrganizationIdentityService = Depends(
            get_organization_identity_service,
        ),
    ) -> PaginatedResponse[OrganizationIdentityResponse]:
        """Obtiene una página filtrada; por defecto solo identidades `ACTIVE`."""
        result = service.list_all(
            page=pagination.page,
            page_size=pagination.page_size,
            search=filters.search,
            country_id=filters.country_id,
            identification_type=filters.identification_type,
            registration_status=filters.registration_status,
            status=filters.status,
        )

        return PaginatedResponse(
            items=result.items,
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.get(
        "/{organization_identity_id}",
        response_model=OrganizationIdentityResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar una identidad de organización",
    )
    def get_organization_identity(
        organization_identity_id: UUID,
        service: OrganizationIdentityService = Depends(
            get_organization_identity_service,
        ),
    ):
        """Obtiene una organización por UUID en cualquier estado (contrato Provider)."""
        return service.get_by_id(organization_identity_id)

    @router.post(
        "",
        response_model=OrganizationIdentityResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Crear una identidad de organización",
    )
    def create_organization_identity(
        payload: OrganizationIdentityCreate,
        actor_id: CurrentSubject,
        response: Response,
        service: OrganizationIdentityService = Depends(
            get_organization_identity_service,
        ),
    ):
        """Crea una identidad global de organización."""
        organization_identity = service.create(
            **payload.model_dump(),
            actor_id=actor_id,
        )
        response.headers["Location"] = (
            f"/api/v1{BASE_PATH}/{organization_identity.id}"
        )

        return organization_identity

    @router.put(
        "/{organization_identity_id}",
        response_model=OrganizationIdentityResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Actualizar una identidad de organización",
    )
    def update_organization_identity(
        organization_identity_id: UUID,
        payload: OrganizationIdentityUpdate,
        actor_id: CurrentSubject,
        service: OrganizationIdentityService = Depends(
            get_organization_identity_service,
        ),
    ):
        """Modifica una organización; un `PUT` sin cambios no escribe (FR-029)."""
        data = payload.model_dump()
        expected_version = data.pop("version")

        return service.update(
            organization_identity_id,
            expected_version=expected_version,
            actor_id=actor_id,
            **data,
        )

    @router.post(
        "/{organization_identity_id}/deactivate",
        response_model=OrganizationIdentityResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "delete")],
        summary="Inactivar una identidad de organización (no elimina)",
    )
    def deactivate_organization_identity(
        organization_identity_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        service: OrganizationIdentityService = Depends(
            get_organization_identity_service,
        ),
    ):
        """Inactiva la organización conservándola (D7, DS-11)."""
        return service.deactivate(
            organization_identity_id,
            expected_version=payload.version,
            actor_id=actor_id,
        )

    @router.post(
        "/{organization_identity_id}/reactivate",
        response_model=OrganizationIdentityResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Reactivar una identidad de organización",
    )
    def reactivate_organization_identity(
        organization_identity_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        service: OrganizationIdentityService = Depends(
            get_organization_identity_service,
        ),
    ):
        """Reactiva una organización inactiva (DS-11)."""
        return service.reactivate(
            organization_identity_id,
            expected_version=payload.version,
            actor_id=actor_id,
        )

    return router
