"""Router HTTP de personas de contacto (contracts/rest-api.md §2)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sio_auth import CurrentSubject, SIOAuth

from party_identity_service.api.dependencies import get_contact_person_service
from party_identity_service.api.pagination import PaginationParams
from party_identity_service.api.schemas.contact_person import (
    ContactPersonCreate,
    ContactPersonResponse,
    ContactPersonUpdate,
    VersionRequest,
)
from party_identity_service.api.schemas.pagination import PaginatedResponse
from party_identity_service.application.contact_person_service import ContactPersonService

SERVICE = "party-identity"
RESOURCE = "organization_contact_persons"


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=["Personas de contacto"])
    collection = "/organization-identities/{organization_identity_id}/contact-persons"
    item = "/organization-contact-persons/{contact_id}"

    @router.get(
        collection,
        response_model=PaginatedResponse[ContactPersonResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar las personas de contacto de una organización",
    )
    def list_contacts(
        organization_identity_id: UUID,
        is_active: bool = Query(default=True, description="Estado reversible ACTIVE/INACTIVE."),
        pagination: PaginationParams = Depends(),
        service: ContactPersonService = Depends(get_contact_person_service),
    ):
        result = service.list_by_organization(
            organization_identity_id, is_active=is_active, page=pagination.page, page_size=pagination.page_size
        )
        return PaginatedResponse(
            items=result.items,
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.post(
        collection,
        response_model=ContactPersonResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Registrar una persona de contacto",
    )
    def create_contact(
        organization_identity_id: UUID,
        payload: ContactPersonCreate,
        actor_id: CurrentSubject,
        service: ContactPersonService = Depends(get_contact_person_service),
    ):
        return service.create(organization_identity_id, **payload.model_dump(), actor_id=actor_id)

    @router.get(
        item,
        response_model=ContactPersonResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar una persona de contacto por UUID (contrato Provider)",
    )
    def get_contact(contact_id: UUID, service: ContactPersonService = Depends(get_contact_person_service)):
        return service.get(contact_id)

    @router.put(
        item,
        response_model=ContactPersonResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Modificar una persona de contacto (is_primary no se modifica aquí)",
    )
    def update_contact(
        contact_id: UUID,
        payload: ContactPersonUpdate,
        actor_id: CurrentSubject,
        service: ContactPersonService = Depends(get_contact_person_service),
    ):
        immutable = [
            name for name in ("is_primary", "organization_identity_id") if getattr(payload, name) is not None
        ]
        return service.update(
            contact_id,
            expected_version=payload.version,
            person_identity_id=payload.person_identity_id,
            position=payload.position,
            email=payload.email,
            phone=payload.phone,
            actor_id=actor_id,
            immutable_fields=immutable,
        )

    @router.post(
        f"{item}:set-primary",
        response_model=ContactPersonResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Establecer el contacto principal (atómico)",
    )
    def set_primary(
        contact_id: UUID,
        payload: VersionRequest,
        actor_id: CurrentSubject,
        service: ContactPersonService = Depends(get_contact_person_service),
    ):
        return service.set_primary(contact_id, expected_version=payload.version, actor_id=actor_id)

    @router.post(
        f"{item}:deactivate",
        response_model=ContactPersonResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "delete")],
        summary="Inactivar una persona de contacto (no elimina)",
    )
    def deactivate(
        contact_id: UUID,
        payload: VersionRequest,
        actor_id: CurrentSubject,
        service: ContactPersonService = Depends(get_contact_person_service),
    ):
        return service.deactivate(contact_id, expected_version=payload.version, actor_id=actor_id)

    @router.post(
        f"{item}:reactivate",
        response_model=ContactPersonResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Reactivar una persona de contacto",
    )
    def reactivate(
        contact_id: UUID,
        payload: VersionRequest,
        actor_id: CurrentSubject,
        service: ContactPersonService = Depends(get_contact_person_service),
    ):
        return service.reactivate(contact_id, expected_version=payload.version, actor_id=actor_id)

    return router
