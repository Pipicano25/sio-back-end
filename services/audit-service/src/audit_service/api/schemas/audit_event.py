"""Esquemas HTTP del evento de auditoría (`contracts/rest-api.md`, `audit-event.md`).

`AuditEventIn` usa `extra="forbid"`: cualquier campo no definido, incluidos los
que fija Audit (`id`, `source_service`, `recorded_at`, `created_by`), responde
`422` (DS-04). Las reglas de formato y límites las aplica `sio_audit.event`
sobre el contenido ya redactado (FR-017b); aquí solo se interpretan los tipos.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sio_audit.event import AuditEvent


class AuditEventIn(BaseModel):
    """Evento que envía un servicio emisor (contrato v1)."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    company_id: UUID | None = None
    branch_id: UUID | None = None
    application_user_id: UUID | None = None
    keycloak_user_id: UUID | None = None
    username_snapshot: str | None = None
    action: str
    entity_type: str
    entity_id: UUID | None = None
    previous_values: dict[str, Any] | None = None
    new_values: dict[str, Any] | None = None
    redacted_paths: list[str] = Field(default_factory=list)
    result: str
    reason: str | None = None
    request_id: UUID | None = None
    correlation_id: UUID | None = None
    occurred_at: datetime

    def to_event(self) -> AuditEvent:
        """Evento del contrato, sin preparar (la redacción ocurre en la aplicación)."""
        return AuditEvent(
            event_id=self.event_id,
            company_id=self.company_id,
            branch_id=self.branch_id,
            application_user_id=self.application_user_id,
            keycloak_user_id=self.keycloak_user_id,
            username_snapshot=self.username_snapshot,
            action=self.action,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            previous_values=self.previous_values,
            new_values=self.new_values,
            redacted_paths=tuple(self.redacted_paths),
            result=self.result,
            reason=self.reason,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            occurred_at=self.occurred_at,
        )


class AuditEventBatchIn(BaseModel):
    """Lote de 1 a 100 eventos (DS-02)."""

    model_config = ConfigDict(extra="forbid")

    events: list[AuditEventIn] = Field(min_length=1, max_length=100)


class AuditEventResponse(BaseModel):
    """Evento registrado. `recorded_at` es la columna `created_at` (DS-10); no expone la huella."""

    id: UUID
    event_id: UUID
    company_id: UUID | None
    branch_id: UUID | None
    application_user_id: UUID | None
    keycloak_user_id: UUID | None
    username_snapshot: str | None
    action: str
    entity_type: str
    entity_id: UUID | None
    previous_values: dict[str, Any] | None
    new_values: dict[str, Any] | None
    redacted_paths: list[str]
    result: str
    reason: str | None
    request_id: UUID | None
    correlation_id: UUID | None
    source_service: str
    occurred_at: datetime
    recorded_at: datetime
    created_by: str

    @classmethod
    def from_row(cls, row: Any) -> AuditEventResponse:
        return cls(
            id=row.id,
            event_id=row.event_id,
            company_id=row.company_id,
            branch_id=row.branch_id,
            application_user_id=row.application_user_id,
            keycloak_user_id=row.keycloak_user_id,
            username_snapshot=row.username_snapshot,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            previous_values=row.previous_values,
            new_values=row.new_values,
            redacted_paths=list(row.redacted_paths or []),
            result=row.result,
            reason=row.reason,
            request_id=row.request_id,
            correlation_id=row.correlation_id,
            source_service=row.source_service,
            occurred_at=row.occurred_at,
            recorded_at=row.created_at,
            created_by=row.created_by,
        )


class BatchItem(BaseModel):
    """Resultado de un evento del lote."""

    index: int
    event_id: UUID
    id: UUID
    outcome: Literal["CREATED", "ALREADY_EXISTS"]


class AuditEventBatchResponse(BaseModel):
    """Resultado de un lote registrado completo."""

    items: list[BatchItem]


class AuditEventPage(BaseModel):
    """Página de eventos (`items`, `page`, `page_size`, `total_records`, `total_pages`)."""

    items: list[AuditEventResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int
