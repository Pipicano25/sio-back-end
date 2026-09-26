"""Router HTTP para identidades globales de personas.

Los errores de aplicación los traduce `api/errors.py`; este módulo no asigna
estados HTTP de error.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from party_identity_service.api.dependencies import get_person_identity_service
from party_identity_service.api.filters.person_identity import (
    PersonIdentityFilters,
)
from party_identity_service.api.pagination import PaginationParams
from party_identity_service.api.schemas.pagination import PaginatedResponse
from party_identity_service.api.schemas.person_identity import (
    PersonIdentityCreate,
    PersonIdentityResponse,
    PersonIdentityUpdate,
)
from party_identity_service.api.schemas.status_action import StatusActionRequest
from party_identity_service.application.person_identity_service import (
    PersonIdentityService,
)

SERVICE = "party-identity"
RESOURCE = "person_identities"
BASE_PATH = "/person-identities"


def build_router(
    auth: SIOAuth,
) -> APIRouter:
    """Construye el router de identidades de personas."""
    router = APIRouter(
        prefix=BASE_PATH,
        tags=["Identidades de personas"],
    )

    @router.get(
        "",
        response_model=PaginatedResponse[PersonIdentityResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar identidades de personas",
    )
    def list_person_identities(
        pagination: PaginationParams = Depends(),
        filters: PersonIdentityFilters = Depends(),
        service: PersonIdentityService = Depends(get_person_identity_service),
    ) -> PaginatedResponse[PersonIdentityResponse]:
        """Obtiene una página filtrada; por defecto solo identidades `ACTIVE`."""
        result = service.list_all(
            page=pagination.page,
            page_size=pagination.page_size,
            search=filters.search,
            identification_country_id=filters.identification_country_id,
            identification_type=filters.identification_type,
            verification_status=filters.verification_status,
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
        "/{person_identity_id}",
        response_model=PersonIdentityResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar una identidad de persona",
    )
    def get_person_identity(
        person_identity_id: UUID,
        service: PersonIdentityService = Depends(get_person_identity_service),
    ):
        """Obtiene una persona por UUID en cualquier estado (contrato Provider)."""
        return service.get_by_id(person_identity_id)

    @router.post(
        "",
        response_model=PersonIdentityResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Crear una identidad de persona",
    )
    def create_person_identity(
        payload: PersonIdentityCreate,
        actor_id: CurrentSubject,
        response: Response,
        service: PersonIdentityService = Depends(get_person_identity_service),
    ):
        """Crea una identidad global de persona."""
        person_identity = service.create(
            **payload.model_dump(),
            actor_id=actor_id,
        )
        response.headers["Location"] = f"/api/v1{BASE_PATH}/{person_identity.id}"

        return person_identity

    @router.put(
        "/{person_identity_id}",
        response_model=PersonIdentityResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Actualizar una identidad de persona",
    )
    def update_person_identity(
        person_identity_id: UUID,
        payload: PersonIdentityUpdate,
        actor_id: CurrentSubject,
        service: PersonIdentityService = Depends(get_person_identity_service),
    ):
        """Modifica una persona; un `PUT` sin cambios no escribe (FR-029)."""
        data = payload.model_dump()
        expected_version = data.pop("version")

        return service.update(
            person_identity_id,
            expected_version=expected_version,
            actor_id=actor_id,
            **data,
        )

    @router.post(
        "/{person_identity_id}/deactivate",
        response_model=PersonIdentityResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "delete")],
        summary="Inactivar una identidad de persona (no elimina)",
    )
    def deactivate_person_identity(
        person_identity_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        service: PersonIdentityService = Depends(get_person_identity_service),
    ):
        """Inactiva la persona conservándola (D7, DS-11)."""
        return service.deactivate(
            person_identity_id,
            expected_version=payload.version,
            actor_id=actor_id,
        )

    @router.post(
        "/{person_identity_id}/reactivate",
        response_model=PersonIdentityResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Reactivar una identidad de persona",
    )
    def reactivate_person_identity(
        person_identity_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        service: PersonIdentityService = Depends(get_person_identity_service),
    ):
        """Reactiva una persona inactiva (DS-11)."""
        return service.reactivate(
            person_identity_id,
            expected_version=payload.version,
            actor_id=actor_id,
        )

    return router
