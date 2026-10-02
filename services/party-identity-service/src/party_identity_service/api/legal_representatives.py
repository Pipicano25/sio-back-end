"""Router HTTP de representantes legales (contracts/rest-api.md §5)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth

from party_identity_service.api.dependencies import get_legal_representative_service
from party_identity_service.api.pagination import PaginationParams
from party_identity_service.api.schemas.contact_person import VersionRequest
from party_identity_service.api.schemas.legal_representative import (
    LegalRepresentativeCreate,
    LegalRepresentativeResponse,
    LegalRepresentativeSetPrimary,
    LegalRepresentativeUpdate,
)
from party_identity_service.api.schemas.pagination import PaginatedResponse
from party_identity_service.application.legal_representative_service import LegalRepresentativeService

SERVICE = "party-identity"
RESOURCE = "organization_legal_representatives"


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=["Representantes legales"])
    collection = "/organization-identities/{organization_identity_id}/legal-representatives"
    item = "/organization-legal-representatives/{representative_id}"

    @router.get(
        collection,
        response_model=PaginatedResponse[LegalRepresentativeResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar los representantes legales de una organización (contrato Provider)",
    )
    def list_representatives(
        organization_identity_id: UUID,
        state: Literal["active", "closed", "all"] = Query(default="active"),
        pagination: PaginationParams = Depends(),
        service: LegalRepresentativeService = Depends(get_legal_representative_service),
    ):
        result = service.list_by_organization(
            organization_identity_id, state=state, page=pagination.page, page_size=pagination.page_size
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
        response_model=LegalRepresentativeResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Registrar un representante legal",
    )
    def register(
        organization_identity_id: UUID,
        payload: LegalRepresentativeCreate,
        actor_id: CurrentSubject,
        service: LegalRepresentativeService = Depends(get_legal_representative_service),
    ):
        return service.register(organization_identity_id, **payload.model_dump(), actor_id=actor_id)

    @router.post(
        f"{collection}:set-primary",
        response_model=LegalRepresentativeResponse,
        status_code=status.HTTP_201_CREATED,
        responses={200: {"description": "La persona ya es el PRIMARY vigente (sin cambios)"}},
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Establecer el representante PRIMARY (crea el primero o sustituye el vigente)",
    )
    def set_primary(
        organization_identity_id: UUID,
        payload: LegalRepresentativeSetPrimary,
        actor_id: CurrentSubject,
        response: Response,
        service: LegalRepresentativeService = Depends(get_legal_representative_service),
    ):
        representative, created = service.set_primary(
            organization_identity_id, **payload.model_dump(), actor_id=actor_id
        )
        if not created:
            response.status_code = status.HTTP_200_OK
        return representative

    @router.get(
        item,
        response_model=LegalRepresentativeResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar una relación de representación por UUID",
    )
    def get_representative(
        representative_id: UUID,
        service: LegalRepresentativeService = Depends(get_legal_representative_service),
    ):
        return service.get(representative_id)

    @router.put(
        item,
        response_model=LegalRepresentativeResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Modificar cargo o referencia documental",
    )
    def update_representative(
        representative_id: UUID,
        payload: LegalRepresentativeUpdate,
        actor_id: CurrentSubject,
        service: LegalRepresentativeService = Depends(get_legal_representative_service),
    ):
        immutable = [
            name
            for name in ("person_identity_id", "organization_identity_id", "representative_type")
            if getattr(payload, name) is not None
        ]
        return service.update(
            representative_id,
            expected_version=payload.version,
            position=payload.position,
            source_document_reference=payload.source_document_reference,
            actor_id=actor_id,
            immutable_fields=immutable,
        )

    @router.post(
        f"{item}:close",
        response_model=LegalRepresentativeResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "delete")],
        summary="Cerrar una relación de representación (no se reactiva)",
    )
    def close(
        representative_id: UUID,
        payload: VersionRequest,
        actor_id: CurrentSubject,
        service: LegalRepresentativeService = Depends(get_legal_representative_service),
    ):
        return service.close(representative_id, expected_version=payload.version, actor_id=actor_id)

    return router
