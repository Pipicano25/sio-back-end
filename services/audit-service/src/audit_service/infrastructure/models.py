"""Modelo persistente de Audit Service (`data-model.md`).

`audit_events` es una entidad persistente de dominio **inmutable** (Principio VI):
lleva las cuatro columnas de auditoría, que nunca cambian, y no lleva `version`
porque la API no la modifica (Principio VII). La inmutabilidad la garantizan
además los triggers de la migración `0001` (R-06).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Index, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import CHAR, DateTime

from audit_service.infrastructure.database import Base


class AuditEventModel(Base):
    """Evento de auditoría registrado (§11.1 del estándar, BR-11)."""

    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    event_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    company_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    branch_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    application_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    keycloak_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    username_snapshot: Mapped[str | None] = mapped_column(String(160))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    previous_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    new_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    redacted_paths: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("'{}'::text[]")
    )
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    correlation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    source_service: Mapped[str] = mapped_column(String(80), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)

    __table_args__ = (
        CheckConstraint("result IN ('SUCCESS','FAILURE')", name="result"),
        CheckConstraint("action ~ '^[A-Z][A-Z0-9_]{0,49}$'", name="action_format"),
        CheckConstraint("entity_type ~ '^[A-Z][A-Za-z0-9]{0,59}$'", name="entity_type_format"),
        CheckConstraint("branch_id IS NULL OR company_id IS NOT NULL", name="branch_requires_company"),
        CheckConstraint(
            "(previous_values IS NULL OR jsonb_typeof(previous_values) = 'object') "
            "AND (new_values IS NULL OR jsonb_typeof(new_values) = 'object')",
            name="values_are_objects",
        ),
        CheckConstraint(
            "(username_snapshot IS NULL OR (btrim(username_snapshot) <> '' "
            "AND username_snapshot = btrim(username_snapshot))) "
            "AND (reason IS NULL OR (btrim(reason) <> '' AND reason = btrim(reason) "
            "AND char_length(reason) <= 2000)) "
            "AND btrim(source_service) <> ''",
            name="texts_not_blank",
        ),
        CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="content_hash_format"),
        CheckConstraint(
            "updated_at = created_at AND updated_by = created_by",
            name="audit_unchanged",
        ),
        UniqueConstraint("event_id", name="uq_audit_events_event_id"),
        Index(
            "ix_audit_events_company_occurred",
            "company_id",
            text("occurred_at DESC"),
            text("id DESC"),
            postgresql_where=text("company_id IS NOT NULL"),
        ),
        Index(
            "ix_audit_events_company_entity",
            "company_id",
            "entity_type",
            "entity_id",
            "occurred_at",
            "id",
            postgresql_where=text("company_id IS NOT NULL"),
        ),
        Index(
            "ix_audit_events_platform_occurred",
            text("occurred_at DESC"),
            text("id DESC"),
            postgresql_where=text("company_id IS NULL"),
        ),
        Index(
            "ix_audit_events_platform_entity",
            "entity_type",
            "entity_id",
            "occurred_at",
            "id",
            postgresql_where=text("company_id IS NULL"),
        ),
        Index(
            "ix_audit_events_company_actor",
            "company_id",
            "keycloak_user_id",
            text("occurred_at DESC"),
        ),
        Index(
            "ix_audit_events_correlation",
            "correlation_id",
            postgresql_where=text("correlation_id IS NOT NULL"),
        ),
        Index(
            "ix_audit_events_request",
            "request_id",
            postgresql_where=text("request_id IS NOT NULL"),
        ),
    )
