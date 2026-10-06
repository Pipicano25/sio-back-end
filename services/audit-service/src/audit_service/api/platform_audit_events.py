"""Consulta de los eventos de plataforma, sin empresa (`contracts/rest-api.md` rutas 6 a 8).

Exige el permiso independiente `perm:audit:platform-events:read`, sin membresía. Nunca
devuelve eventos de empresa (RC-10).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sio_auth import SIOAuth

from audit_service.api.dependencies import get_query_service
from audit_service.api.company_audit_events import ENTITY_TYPE, SERVICE, page_response
from audit_service.api.filters.audit_event_filters import EntityHistoryQuery, PlatformEventQuery
from audit_service.api.openapi import NOT_FOUND_RESPONSE, TAG_PLATFORM
from audit_service.api.schemas.audit_event import AuditEventPage, AuditEventResponse
from audit_service.application.query_service import QueryService


def build_platform_router(auth: SIOAuth) -> APIRouter:
    """Consultas de eventos de plataforma (sin empresa)."""
    router = APIRouter(tags=[TAG_PLATFORM])
    read = [auth.permission(SERVICE, "platform-events", "read")]

    @router.get(
        "/platform-audit-events",
        response_model=AuditEventPage,
        summary="Listar los eventos de plataforma",
        dependencies=read,
    )
    def list_platform_events(
        query: Annotated[PlatformEventQuery, Query()],
        service: Annotated[QueryService, Depends(get_query_service)],
    ) -> AuditEventPage:
        result = service.list_platform(query.to_filters(), query.page_request())
        return page_response(result, query.page, query.page_size)

    @router.get(
        "/platform-audit-events/{audit_id}",
        response_model=AuditEventResponse,
        summary="Obtener un evento de plataforma",
        responses=NOT_FOUND_RESPONSE,
        dependencies=read,
    )
    def get_platform_event(
        audit_id: UUID,
        service: Annotated[QueryService, Depends(get_query_service)],
    ) -> AuditEventResponse:
        return AuditEventResponse.from_row(service.get_platform(audit_id))

    @router.get(
        "/platform-entity-history/{entity_type}/{entity_id}",
        response_model=AuditEventPage,
        summary="Historial de una entidad de plataforma (orden cronológico)",
        dependencies=read,
    )
    def platform_entity_history(
        entity_type: Annotated[str, ENTITY_TYPE],
        entity_id: UUID,
        query: Annotated[EntityHistoryQuery, Query()],
        service: Annotated[QueryService, Depends(get_query_service)],
    ) -> AuditEventPage:
        result = service.platform_entity_history(
            entity_type, entity_id, query.to_filters(), query.page_request()
        )
        return page_response(result, query.page, query.page_size)

    return router
