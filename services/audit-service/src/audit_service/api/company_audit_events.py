"""Consulta de los eventos de una empresa (`contracts/rest-api.md` rutas 3 a 5).

Exige `perm:audit:audit-events:read` y membresía `ACTIVE` del usuario (Operational Context
con su token). Nunca devuelve eventos de plataforma (RC-10).
"""

from __future__ import annotations

from math import ceil
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sio_auth import SIOAuth

from audit_service.api.dependencies import get_query_service
from audit_service.api.filters.audit_event_filters import (
    CompanyEventQuery,
    EntityHistoryQuery,
)
from audit_service.api.openapi import COMPANY_RESPONSES, TAG_COMPANY
from audit_service.api.schemas.audit_event import AuditEventPage, AuditEventResponse
from audit_service.application.ports import Page
from audit_service.application.query_service import QueryService

SERVICE = "audit"
ENTITY_TYPE = Path(pattern=r"^[A-Z][A-Za-z0-9]{0,59}$", description="Entidad en PascalCase.")


def page_response(result: Page, page: int, page_size: int) -> AuditEventPage:
    return AuditEventPage(
        items=[AuditEventResponse.from_row(row) for row in result.items],
        page=page,
        page_size=page_size,
        total_records=result.total_records,
        total_pages=ceil(result.total_records / page_size) if result.total_records else 0,
    )


def build_company_router(auth: SIOAuth) -> APIRouter:
    """Consultas de eventos de una empresa."""
    router = APIRouter(tags=[TAG_COMPANY], responses=COMPANY_RESPONSES)
    read = [auth.permission(SERVICE, "audit-events", "read")]

    @router.get(
        "/companies/{company_id}/audit-events",
        response_model=AuditEventPage,
        summary="Listar los eventos de una empresa",
        dependencies=read,
    )
    def list_company_events(
        company_id: UUID,
        query: Annotated[CompanyEventQuery, Query()],
        service: Annotated[QueryService, Depends(get_query_service)],
    ) -> AuditEventPage:
        result = service.list_company(company_id, query.to_filters(), query.page_request())
        return page_response(result, query.page, query.page_size)

    @router.get(
        "/companies/{company_id}/audit-events/{audit_id}",
        response_model=AuditEventResponse,
        summary="Obtener un evento de una empresa",
        dependencies=read,
    )
    def get_company_event(
        company_id: UUID,
        audit_id: UUID,
        service: Annotated[QueryService, Depends(get_query_service)],
    ) -> AuditEventResponse:
        return AuditEventResponse.from_row(service.get_company(company_id, audit_id))

    @router.get(
        "/companies/{company_id}/entity-history/{entity_type}/{entity_id}",
        response_model=AuditEventPage,
        summary="Historial de una entidad de la empresa (orden cronológico)",
        dependencies=read,
    )
    def company_entity_history(
        company_id: UUID,
        entity_type: Annotated[str, ENTITY_TYPE],
        entity_id: UUID,
        query: Annotated[EntityHistoryQuery, Query()],
        service: Annotated[QueryService, Depends(get_query_service)],
    ) -> AuditEventPage:
        result = service.company_entity_history(
            company_id, entity_type, entity_id, query.to_filters(), query.page_request()
        )
        return page_response(result, query.page, query.page_size)

    return router


