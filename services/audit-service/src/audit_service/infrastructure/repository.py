"""Repositorio de `audit_events`: solo inserción idempotente y lectura (RC-02, RC-05).

- `insert_or_get` usa `INSERT … ON CONFLICT (event_id) DO NOTHING RETURNING`: los
  reenvíos concurrentes del mismo evento producen una sola fila sin `500` por
  violación de unicidad (R-04). Si el evento ya existía se lee y se compara su
  `content_hash` con el recibido.
- Toda consulta lleva el alcance en SQL: `company_id = :company_id` (empresa) o
  `company_id IS NULL` (plataforma). Ningún filtro puede cambiarlo (RC-10).

No existen métodos de modificación ni de eliminación.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from audit_service.application.ports import (
    AuditEventFilters,
    InsertOutcome,
    NewAuditEventRow,
    Page,
)
from audit_service.infrastructure.models import AuditEventModel

_FILTER_COLUMNS = (
    "action",
    "entity_type",
    "entity_id",
    "result",
    "source_service",
    "keycloak_user_id",
    "application_user_id",
    "branch_id",
    "event_id",
    "correlation_id",
    "request_id",
)


class SqlAlchemyAuditEventRepository:
    """Repositorio sobre una sesión SQLAlchemy por solicitud."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def database_now(self) -> datetime:
        """Hora de la base, referencia para el límite de `occurred_at` (DS-08)."""
        return self._session.execute(text("SELECT now()")).scalar_one()

    def insert_or_get(self, rows: Sequence[NewAuditEventRow]) -> list[InsertOutcome]:
        """Inserta cada evento o, si su `event_id` existe, lo lee y compara su huella.

        No confirma la transacción: el servicio de aplicación decide `commit` o
        `rollback` (lote atómico, RC-06).
        """
        outcomes: list[InsertOutcome] = []

        for row in rows:
            statement = (
                insert(AuditEventModel)
                .values(**row.values)
                .on_conflict_do_nothing(index_elements=["event_id"])
                .returning(AuditEventModel.id)
            )
            inserted_id = self._session.execute(statement).scalar_one_or_none()

            if inserted_id is not None:
                created = self._session.get(AuditEventModel, inserted_id, populate_existing=True)
                outcomes.append(
                    InsertOutcome(event_id=row.event_id, row=created, created=True, conflict=False)
                )
                continue

            existing = self._session.execute(
                select(AuditEventModel).where(AuditEventModel.event_id == row.event_id)
            ).scalar_one()
            outcomes.append(
                InsertOutcome(
                    event_id=row.event_id,
                    row=existing,
                    created=False,
                    conflict=existing.content_hash != row.content_hash,
                )
            )

        return outcomes

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()

    @staticmethod
    def _scope(company_id: UUID | None) -> ColumnElement[bool]:
        if company_id is None:
            return AuditEventModel.company_id.is_(None)
        return AuditEventModel.company_id == company_id

    def get(self, audit_id: UUID, *, company_id: UUID | None) -> AuditEventModel | None:
        """Evento por `id` dentro del alcance (`company_id` o plataforma si es `None`)."""
        return self._session.execute(
            select(AuditEventModel).where(
                AuditEventModel.id == audit_id, self._scope(company_id)
            )
        ).scalar_one_or_none()

    def list(
        self,
        *,
        company_id: UUID | None,
        filters: AuditEventFilters,
        page: int,
        page_size: int,
        ascending: bool = False,
    ) -> Page:
        """Página de eventos del alcance, ordenada por `occurred_at` e `id`."""
        conditions: list[ColumnElement[bool]] = [self._scope(company_id)]

        for name in _FILTER_COLUMNS:
            value = getattr(filters, name)
            if value is not None:
                conditions.append(getattr(AuditEventModel, name) == value)

        if filters.occurred_at_from is not None:
            conditions.append(AuditEventModel.occurred_at >= filters.occurred_at_from)

        if filters.occurred_at_to is not None:
            conditions.append(AuditEventModel.occurred_at <= filters.occurred_at_to)

        total = self._session.execute(
            select(func.count()).select_from(AuditEventModel).where(*conditions)
        ).scalar_one()

        order = (
            (AuditEventModel.occurred_at.asc(), AuditEventModel.id.asc())
            if ascending
            else (AuditEventModel.occurred_at.desc(), AuditEventModel.id.desc())
        )
        items = (
            self._session.execute(
                select(AuditEventModel)
                .where(*conditions)
                .order_by(*order)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )

        return Page(items=items, total_records=total)
