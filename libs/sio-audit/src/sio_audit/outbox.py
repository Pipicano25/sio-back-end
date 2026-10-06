"""Transactional Outbox de auditoría para los servicios emisores (FR-075, FR-077; R-11).

- `audit_outbox_table(metadata)`: definición de la tabla en la metadata del emisor.
- `create_audit_outbox_table(op)` / `drop_audit_outbox_table(op)`: para la migración
  Alembic del emisor (la librería no ejecuta migraciones por sí sola).
- `record_audit_event(session, event)`: prepara el evento (recorte, **redacción** y
  validación, `sio_audit.event.prepare_event`) y lo inserta en la sesión del emisor,
  dentro de su transacción de negocio. No hace `commit`.

Categoría Outbox del Principio VI; metadatos declarados citando D26 (data-model.md).
El `payload` guarda el evento canónico **ya redactado**: ningún valor sensible llega a
la outbox.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Table,
    insert,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session

from sio_audit.event import AuditEvent, InvalidAuditEventError, prepare_event, to_canonical_dict

__all__ = [
    "OUTBOX_TABLE",
    "InvalidAuditEventError",
    "audit_outbox_table",
    "create_audit_outbox_table",
    "drop_audit_outbox_table",
    "record_audit_event",
]

OUTBOX_TABLE = "audit_outbox"
PENDING = "PENDING"
SENT = "SENT"


def _columns() -> list[Any]:
    return [
        Column("event_id", PG_UUID(as_uuid=True), nullable=False),
        Column("payload", JSONB, nullable=False),
        Column("status", String(20), nullable=False, server_default=text("'PENDING'")),
        Column("attempts", Integer, nullable=False, server_default=text("0")),
        Column("next_attempt_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
        Column("last_status_code", SmallInteger, nullable=True),
        Column("last_error_code", String(80), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
        Column("sent_at", DateTime(timezone=True), nullable=True),
    ]


def _constraints() -> list[Any]:
    return [
        PrimaryKeyConstraint("event_id", name="pk_audit_outbox"),
        CheckConstraint("status IN ('PENDING','SENT')", name="ck_audit_outbox_status"),
        CheckConstraint(
            "(status = 'SENT') = (sent_at IS NOT NULL)", name="ck_audit_outbox_sent_at"
        ),
        CheckConstraint("attempts >= 0", name="ck_audit_outbox_attempts_non_negative"),
    ]


def audit_outbox_table(metadata: MetaData) -> Table:
    """Define `audit_outbox` en la metadata del emisor (nombres de restricción explícitos)."""
    table = Table(OUTBOX_TABLE, metadata, *_columns(), *_constraints())
    Index(
        "ix_audit_outbox_pending",
        table.c.next_attempt_at,
        postgresql_where=text("status = 'PENDING'"),
    )
    return table


def create_audit_outbox_table(op: Any) -> None:
    """Crea la tabla desde una migración Alembic del emisor (`op` de Alembic)."""
    op.create_table(OUTBOX_TABLE, *_columns(), *_constraints())
    op.create_index(
        "ix_audit_outbox_pending",
        OUTBOX_TABLE,
        ["next_attempt_at"],
        postgresql_where=text("status = 'PENDING'"),
    )


def drop_audit_outbox_table(op: Any) -> None:
    """Elimina la tabla desde el `downgrade` de la migración del emisor."""
    op.drop_index("ix_audit_outbox_pending", table_name=OUTBOX_TABLE)
    op.drop_table(OUTBOX_TABLE)


_OUTBOX = audit_outbox_table(MetaData())


def record_audit_event(session: Session, event: AuditEvent) -> UUID:
    """Registra el evento en la outbox dentro de la transacción en curso del emisor.

    Si `event.event_id` es `None` se asigna uno nuevo; ese `event_id` se conserva en
    todos los reintentos del worker.

    Raises:
        InvalidAuditEventError: Si el evento no cumple el contrato (error de programación
            del emisor; debe detectarse en sus pruebas).
    """
    if event.event_id is None:
        event = replace(event, event_id=uuid4())

    prepared = prepare_event(event)
    session.execute(
        insert(_OUTBOX).values(event_id=prepared.event_id, payload=to_canonical_dict(prepared))
    )
    return prepared.event_id
