"""Puertos de Audit Service (Principio XV).

Las pruebas sustituyen los adaptadores por dobles inyectados en `create_app`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CompanyAccess:
    """Resultado de `operational-access` para una empresa."""

    member_active: bool


class CompanyAccessDirectory(Protocol):
    """Operational Context: membresía del usuario en una empresa (FR-033, FR-050)."""

    def check_company_access(self, company_id: UUID) -> CompanyAccess:
        """Raises `OperationalAccessDeniedError` o `DependencyUnavailableError`."""
        ...


@dataclass(frozen=True, slots=True)
class NewAuditEventRow:
    """Fila lista para insertar (evento ya preparado y redactado)."""

    event_id: UUID
    values: dict[str, Any]
    content_hash: str


@dataclass(frozen=True, slots=True)
class InsertOutcome:
    """Resultado de insertar o encontrar un evento por `event_id`."""

    event_id: UUID
    row: Any
    created: bool
    conflict: bool


@dataclass(frozen=True, slots=True)
class AuditEventFilters:
    """Filtros de consulta (ninguno decide el alcance: lo decide la ruta)."""

    occurred_at_from: datetime | None = None
    occurred_at_to: datetime | None = None
    action: str | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    result: str | None = None
    source_service: str | None = None
    keycloak_user_id: UUID | None = None
    application_user_id: UUID | None = None
    branch_id: UUID | None = None
    event_id: UUID | None = None
    correlation_id: UUID | None = None
    request_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Page:
    """Página de resultados."""

    items: Sequence[Any]
    total_records: int


class AuditEventRepository(Protocol):
    """Persistencia de `audit_events` (solo inserción y lectura)."""

    def database_now(self) -> datetime: ...

    def insert_or_get(self, rows: Sequence[NewAuditEventRow]) -> list[InsertOutcome]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...

    def get(self, event_id: UUID, *, company_id: UUID | None) -> Any | None: ...

    def list(
        self,
        *,
        company_id: UUID | None,
        filters: AuditEventFilters,
        page: int,
        page_size: int,
        ascending: bool = False,
    ) -> Page: ...
