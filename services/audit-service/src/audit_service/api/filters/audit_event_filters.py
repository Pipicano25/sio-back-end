"""Parámetros de consulta (`contracts/rest-api.md` rutas 3 a 8).

Modelos con `extra="forbid"`: un parámetro desconocido responde `422`. Ningún
parámetro decide el alcance (empresa o plataforma): lo decide la ruta (RC-10).
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from audit_service.application.exceptions import ValidationFailedError
from audit_service.application.ports import AuditEventFilters
from audit_service.application.query_service import PageRequest


class _BaseQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1, description="Número de página solicitado.")
    page_size: int = Field(default=20, ge=1, le=100, description="Registros por página (máximo 100).")
    occurred_at_from: datetime | None = Field(default=None, description="Desde (con zona horaria).")
    occurred_at_to: datetime | None = Field(default=None, description="Hasta (con zona horaria).")
    result: Literal["SUCCESS", "FAILURE"] | None = None

    @field_validator("occurred_at_from", "occurred_at_to")
    @classmethod
    def _require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Debe incluir zona horaria.")
        return value

    def page_request(self) -> PageRequest:
        return PageRequest(page=self.page, page_size=self.page_size)

    def _check_range(self) -> None:
        if (
            self.occurred_at_from is not None
            and self.occurred_at_to is not None
            and self.occurred_at_from > self.occurred_at_to
        ):
            raise ValidationFailedError(
                "La solicitud contiene datos inválidos.",
                errors=[
                    {
                        "field": "occurred_at_from",
                        "message": "Debe ser anterior o igual a occurred_at_to.",
                        "code": "VALIDATION_ERROR",
                    }
                ],
            )


class EntityHistoryQuery(_BaseQuery):
    """Historial de una entidad (rutas 5 y 8)."""

    def to_filters(self) -> AuditEventFilters:
        self._check_range()
        return AuditEventFilters(
            occurred_at_from=self.occurred_at_from,
            occurred_at_to=self.occurred_at_to,
            result=self.result,
        )


class PlatformEventQuery(_BaseQuery):
    """Listado de eventos de plataforma (ruta 6)."""

    action: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    source_service: str | None = None
    keycloak_user_id: UUID | None = None
    application_user_id: UUID | None = None
    event_id: UUID | None = None
    correlation_id: UUID | None = None
    request_id: UUID | None = None

    def to_filters(self) -> AuditEventFilters:
        self._check_range()
        return AuditEventFilters(
            occurred_at_from=self.occurred_at_from,
            occurred_at_to=self.occurred_at_to,
            result=self.result,
            action=self.action,
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            source_service=self.source_service,
            keycloak_user_id=self.keycloak_user_id,
            application_user_id=self.application_user_id,
            event_id=self.event_id,
            correlation_id=self.correlation_id,
            request_id=self.request_id,
        )


class CompanyEventQuery(PlatformEventQuery):
    """Listado de eventos de una empresa (ruta 3): suma el filtro de sucursal."""

    branch_id: UUID | None = None

    def to_filters(self) -> AuditEventFilters:
        return replace(super().to_filters(), branch_id=self.branch_id)
