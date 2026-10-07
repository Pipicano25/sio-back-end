"""Hitos logísticos (`contracts/rest-api.md` rutas 13–14)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status
from sio_auth import SIOAuth

from purchase_service.api.dependencies import ActorDep, CompanyReader, ServicesDep
from purchase_service.api.identity import SERVICE
from purchase_service.api.openapi import READ_RESPONSES, TAG_EVENTS, WRITE_RESPONSES
from purchase_service.api.schemas.others import LifecycleEventIn, LifecycleEventResponse, TimelineResponse


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_EVENTS])
    path = "/companies/{company_id}/purchases/{purchase_id}/lifecycle-events"

    @router.post(
        path,
        status_code=status.HTTP_201_CREATED,
        response_model=LifecycleEventResponse,
        response_model_exclude_none=True,
        summary="Registrar un hito logístico (inmutable)",
        responses=WRITE_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_lifecycle_events", "create")],
    )
    def record_event(
        company_id: UUID, purchase_id: UUID, body: LifecycleEventIn, actor: ActorDep, services: ServicesDep
    ) -> LifecycleEventResponse:
        event = services.lifecycle().record(
            company_id, purchase_id, body.event_type, body.occurred_at, body.source, body.notes, actor
        )
        return LifecycleEventResponse.of(event)

    @router.get(
        path,
        response_model=TimelineResponse,
        summary="Línea de tiempo: hitos, vigentes, intervalos y lead time total",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_lifecycle_events", "read")],
    )
    def timeline(company_id: CompanyReader, purchase_id: UUID, services: ServicesDep) -> TimelineResponse:
        return TimelineResponse.of(services.lifecycle().timeline(company_id, purchase_id))

    return router
