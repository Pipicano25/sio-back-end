"""Secuencias de numeración (`contracts/rest-api.md` rutas 15–19).

Usuario humano con `perm:purchase:purchase_sequences:*` y membresía `ACTIVE` en la
empresa (no exige asignación a sucursal).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from sio_auth import SIOAuth

from purchase_service.api.dependencies import ActorDep, ServicesDep
from purchase_service.api.identity import SERVICE
from purchase_service.api.openapi import SEQUENCE_RESPONSES, TAG_SEQUENCES
from purchase_service.api.schemas.others import SequenceIn, SequenceList, SequenceResponse, SequenceUpdateIn
from purchase_service.api.schemas.purchases import VersionIn


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_SEQUENCES])
    base = "/companies/{company_id}/purchase-sequences"

    @router.post(
        base,
        status_code=status.HTTP_201_CREATED,
        response_model=SequenceResponse,
        summary="Crear una secuencia (queda activa)",
        responses=SEQUENCE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_sequences", "create")],
    )
    def create_sequence(company_id: UUID, body: SequenceIn, actor: ActorDep, services: ServicesDep) -> SequenceResponse:
        return SequenceResponse.of(services.sequence_service().create(company_id, body.to_data(), actor))

    @router.get(
        base,
        response_model=SequenceList,
        summary="Secuencias de la empresa con sus contadores por período",
        responses=SEQUENCE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_sequences", "read")],
    )
    def list_sequences(company_id: UUID, actor: ActorDep, services: ServicesDep) -> SequenceList:
        return SequenceList(items=[SequenceResponse.of(view) for view in services.sequence_service().list(company_id, actor)])

    @router.get(
        base + "/{sequence_id}",
        response_model=SequenceResponse,
        summary="Secuencia por id",
        responses=SEQUENCE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_sequences", "read")],
    )
    def get_sequence(company_id: UUID, sequence_id: UUID, actor: ActorDep, services: ServicesDep) -> SequenceResponse:
        return SequenceResponse.of(services.sequence_service().get(company_id, sequence_id, actor))

    @router.put(
        base + "/{sequence_id}",
        response_model=SequenceResponse,
        summary="Modificar una secuencia (formato inmutable tras el primer número)",
        responses=SEQUENCE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_sequences", "update")],
    )
    def update_sequence(
        company_id: UUID, sequence_id: UUID, body: SequenceUpdateIn, actor: ActorDep, services: ServicesDep
    ) -> SequenceResponse:
        view = services.sequence_service().update(company_id, sequence_id, body.to_data(), body.version, actor)
        return SequenceResponse.of(view)

    @router.post(
        base + "/{sequence_id}/deactivate",
        response_model=SequenceResponse,
        summary="Desactivar una secuencia",
        responses=SEQUENCE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_sequences", "update")],
    )
    def deactivate_sequence(
        company_id: UUID, sequence_id: UUID, body: VersionIn, actor: ActorDep, services: ServicesDep
    ) -> SequenceResponse:
        return SequenceResponse.of(services.sequence_service().set_active(company_id, sequence_id, False, body.version, actor))

    @router.post(
        base + "/{sequence_id}/reactivate",
        response_model=SequenceResponse,
        summary="Activar una secuencia (a lo sumo una activa por alcance)",
        responses=SEQUENCE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_sequences", "update")],
    )
    def reactivate_sequence(
        company_id: UUID, sequence_id: UUID, body: VersionIn, actor: ActorDep, services: ServicesDep
    ) -> SequenceResponse:
        return SequenceResponse.of(services.sequence_service().set_active(company_id, sequence_id, True, body.version, actor))

    return router
