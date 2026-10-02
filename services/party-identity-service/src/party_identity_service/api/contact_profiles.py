"""Router HTTP de perfiles de contacto de personas y organizaciones (§1).

Los errores de aplicación los traduce `api/errors.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from party_identity_service.api.dependencies import (
    get_organization_contact_profile_service,
    get_person_contact_profile_service,
)
from party_identity_service.api.pagination import PaginationParams
from party_identity_service.api.schemas.contact_profile import (
    ContactProfileClose,
    ContactProfileCreate,
    OrganizationContactProfileResponse,
    PersonContactProfileResponse,
)
from party_identity_service.api.schemas.pagination import PaginatedResponse
from party_identity_service.application.contact_profile_service import ContactProfileService

SERVICE = "party-identity"

Kind = Literal["person", "organization"]


def build_router(auth: SIOAuth, kind: Kind) -> APIRouter:
    """Construye el router de perfiles de un tipo de parte."""
    resource = f"{kind}_contact_profiles"
    owner_param = f"{kind}_identity_id"
    response_model = PersonContactProfileResponse if kind == "person" else OrganizationContactProfileResponse
    service_dependency: Callable = (
        get_person_contact_profile_service if kind == "person" else get_organization_contact_profile_service
    )
    identity_path = f"/{kind}-identities/{{{owner_param}}}/contact-profile"
    tag = "Perfiles de contacto de personas" if kind == "person" else "Perfiles de contacto de organizaciones"

    router = APIRouter(tags=[tag])

    @router.get(
        identity_path,
        response_model=response_model,
        dependencies=[auth.permission(SERVICE, resource, "read")],
        summary="Consultar el perfil de contacto vigente",
        operation_id=f"get_current_{kind}_contact_profile",
    )
    def get_current(identity_id: UUID = _path(owner_param), service: ContactProfileService = Depends(service_dependency)):
        return response_model.of(service.get_active(identity_id))

    @router.get(
        f"{identity_path}/versions",
        response_model=PaginatedResponse[response_model],
        dependencies=[auth.permission(SERVICE, resource, "read")],
        summary="Consultar el historial de versiones del perfil",
        operation_id=f"list_{kind}_contact_profile_versions",
    )
    def list_versions(
        identity_id: UUID = _path(owner_param),
        pagination: PaginationParams = Depends(),
        service: ContactProfileService = Depends(service_dependency),
    ):
        result = service.list_versions(identity_id, page=pagination.page, page_size=pagination.page_size)
        return PaginatedResponse(
            items=[response_model.of(item) for item in result.items],
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.get(
        f"/{kind}-contact-profiles/{{profile_id}}",
        response_model=response_model,
        dependencies=[auth.permission(SERVICE, resource, "read")],
        summary="Consultar una versión de perfil por UUID",
        operation_id=f"get_{kind}_contact_profile_version",
    )
    def get_version(profile_id: UUID, service: ContactProfileService = Depends(service_dependency)):
        return response_model.of(service.get_version(profile_id))

    @router.post(
        identity_path,
        response_model=response_model,
        status_code=status.HTTP_201_CREATED,
        responses={200: {"description": "Solicitud idéntica a la vigente (sin cambios)"}},
        dependencies=[auth.permission(SERVICE, resource, "create")],
        summary="Registrar una versión nueva del perfil (confirmada desde una empresa)",
        operation_id=f"register_{kind}_contact_profile",
    )
    def register(
        payload: ContactProfileCreate,
        actor_id: CurrentSubject,
        response: Response,
        identity_id: UUID = _path(owner_param),
        service: ContactProfileService = Depends(service_dependency),
    ):
        data = payload.model_dump()
        expected_version = data.pop("version")
        profile, created = service.register(
            identity_id,
            **data,
            expected_version=expected_version,
            actor_id=actor_id,
            keycloak_user_id=actor_id,
        )
        if not created:
            response.status_code = status.HTTP_200_OK
        return response_model.of(profile)

    @router.post(
        f"{identity_path}:close",
        response_model=response_model,
        dependencies=[auth.permission(SERVICE, resource, "delete")],
        summary="Cerrar el perfil vigente sin reemplazo (no elimina)",
        operation_id=f"close_{kind}_contact_profile",
    )
    def close(
        payload: ContactProfileClose,
        actor_id: CurrentSubject,
        identity_id: UUID = _path(owner_param),
        service: ContactProfileService = Depends(service_dependency),
    ):
        return response_model.of(
            service.close(identity_id, expected_version=payload.version, actor_id=actor_id)
        )

    return router


def _path(name: str):
    from fastapi import Path

    return Path(..., alias=name)
