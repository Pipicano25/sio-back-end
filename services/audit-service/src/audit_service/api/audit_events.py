"""Registro de eventos de auditoría (`contracts/rest-api.md` rutas 1 y 2).

Solo cuentas de servicio con `perm:audit:audit-events:create` (RC-01). No se
publican `PUT`, `PATCH` ni `DELETE`: la API no modifica ni elimina eventos (RC-02).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sio_auth import SIOAuth

from audit_service.api.dependencies import get_registration_service
from audit_service.api.identity import EmitterIdentity, require_service_account
from audit_service.api.openapi import MALFORMED_BODY_RESPONSE, TAG_REGISTRATION
from audit_service.api.schemas.audit_event import (
    AuditEventBatchIn,
    AuditEventBatchResponse,
    AuditEventIn,
    AuditEventResponse,
    BatchItem,
)
from audit_service.application.registration_service import Emitter, RegistrationService

SERVICE = "audit"
RESOURCE = "audit-events"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de registro."""
    router = APIRouter(tags=[TAG_REGISTRATION])

    @router.post(
        "/audit-events",
        status_code=status.HTTP_201_CREATED,
        response_model=AuditEventResponse,
        summary="Registrar un evento de auditoría",
        responses={
            200: {"description": "El evento ya existía con el mismo contenido (idempotente)."},
            409: {"description": "`AUDIT.EVENT_ID_CONFLICT`: event_id existente con contenido o emisor distinto."},
            422: {"description": "`AUDIT.VALIDATION_ERROR`."},
            **MALFORMED_BODY_RESPONSE,
        },
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
    )
    def register_event(
        body: AuditEventIn,
        response: Response,
        identity: Annotated[EmitterIdentity, Depends(require_service_account)],
        service: Annotated[RegistrationService, Depends(get_registration_service)],
    ) -> AuditEventResponse:
        registered = service.register(
            body.to_event(),
            Emitter(subject=identity.subject, source_service=identity.client_id),
        )

        if not registered.created:
            response.status_code = status.HTTP_200_OK

        return AuditEventResponse.from_row(registered.row)

    @router.post(
        "/audit-events/batch",
        status_code=status.HTTP_200_OK,
        response_model=AuditEventBatchResponse,
        summary="Registrar un lote de 1 a 100 eventos (atómico)",
        responses={
            409: {"description": "`AUDIT.EVENT_ID_CONFLICT` con `conflicts`; no se guarda ningún evento."},
            422: {"description": "`AUDIT.VALIDATION_ERROR`; no se guarda ningún evento."},
            **MALFORMED_BODY_RESPONSE,
        },
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
    )
    def register_batch(
        body: AuditEventBatchIn,
        identity: Annotated[EmitterIdentity, Depends(require_service_account)],
        service: Annotated[RegistrationService, Depends(get_registration_service)],
    ) -> AuditEventBatchResponse:
        registered = service.register_batch(
            [item.to_event() for item in body.events],
            Emitter(subject=identity.subject, source_service=identity.client_id),
        )

        return AuditEventBatchResponse(
            items=[
                BatchItem(
                    index=item.index,
                    event_id=item.row.event_id,
                    id=item.row.id,
                    outcome="CREATED" if item.created else "ALREADY_EXISTS",
                )
                for item in registered
            ]
        )

    return router
