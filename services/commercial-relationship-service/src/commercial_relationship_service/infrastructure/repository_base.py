"""Base común de los repositorios SQLAlchemy de las tres entidades.

Las lecturas cierran su transacción implícita al terminar (no retienen
conexiones ni bloqueos mientras se consulta a otros servicios); las escrituras
son transacciones cortas que traducen las violaciones de unicidad por nombre de
restricción (R-08).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from commercial_relationship_service.application.exceptions import CommercialRelationshipError
from commercial_relationship_service.application.pagination import PageResult
from commercial_relationship_service.domain.rules import code_key
from commercial_relationship_service.application import audit_events
from commercial_relationship_service.infrastructure.persistence import (
    commit_or_translate,
    end_read,
    load_for_update,
)

ModelT = TypeVar("ModelT")

DEFAULT_STATUS = "ACTIVE"
ALL_STATUSES = "ALL"


def like_pattern(term: str) -> str:
    """Patrón `ILIKE` de coincidencia parcial con los comodines del usuario escapados."""
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class SQLAlchemyRepositoryBase(Generic[ModelT]):
    """Operaciones comunes; cada subclase fija el modelo y la búsqueda."""

    model: type[ModelT]
    search_columns: tuple[str, ...] = ()
    order_columns: tuple[str, ...] = ("display_name", "id")
    duplicates: dict[str, Callable[[], CommercialRelationshipError]] = {}

    def __init__(self, session: Session) -> None:
        self.session = session

    # -------------------------------------------------------------- lecturas

    def get(self, entity_id: UUID) -> ModelT | None:
        model = self.session.get(self.model, entity_id, populate_existing=True)
        end_read(self.session)
        return model

    def get_many(self, ids: list[UUID]) -> list[ModelT]:
        rows = list(self.session.scalars(select(self.model).where(self.model.id.in_(ids))))
        end_read(self.session)
        return rows

    def code_taken(self, company_id: UUID, internal_code: str, *, exclude_id: UUID | None = None) -> bool:
        statement = select(self.model.id).where(
            self.model.company_id == company_id,
            func.lower(self.model.internal_code) == code_key(internal_code),
        )

        if exclude_id is not None:
            statement = statement.where(self.model.id != exclude_id)

        taken = self.session.scalar(statement.limit(1)) is not None
        end_read(self.session)
        return taken

    def exists_where(self, *conditions: Any) -> bool:
        found = self.session.scalar(select(self.model.id).where(*conditions).limit(1)) is not None
        end_read(self.session)
        return found

    def list_page(
        self,
        company_id: UUID,
        *,
        status: str | None,
        search: str | None,
        filters: dict[str, Any],
        page: int,
        page_size: int,
        conditions: tuple[Any, ...] = (),
    ) -> PageResult[ModelT]:
        statement: Select = select(self.model).where(self.model.company_id == company_id, *conditions)

        effective_status = status or DEFAULT_STATUS

        if effective_status != ALL_STATUSES:
            statement = statement.where(self.model.status == effective_status)

        if search:
            pattern = like_pattern(search)
            statement = statement.where(
                or_(
                    *(
                        getattr(self.model, column).ilike(pattern, escape="\\")
                        for column in self.search_columns
                    )
                )
            )

        for column, value in filters.items():
            if value is not None:
                statement = statement.where(getattr(self.model, column) == value)

        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        rows = list(
            self.session.scalars(
                statement.order_by(*(getattr(self.model, column) for column in self.order_columns))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        end_read(self.session)

        return PageResult(items=rows, page=page, page_size=page_size, total_records=total)

    def count_by_company_status(self, company_ids: list[UUID]) -> dict[UUID, dict[str, int]]:
        """Conteo por empresa y estado en una sola consulta agrupada (resumen, FR-046)."""
        if not company_ids:
            return {}

        rows = self.session.execute(
            select(self.model.company_id, self.model.status, func.count())
            .where(self.model.company_id.in_(company_ids))
            .group_by(self.model.company_id, self.model.status)
        ).all()
        end_read(self.session)

        counts: dict[UUID, dict[str, int]] = {}
        for company_id, status, total in rows:
            counts.setdefault(company_id, {})[status] = total
        return counts

    # ------------------------------------------------------------- escrituras

    def create(self, *, audit: dict[str, Any] | None = None, **fields: Any) -> ModelT:
        """Inserta una fila nueva traduciendo las unicidades de la entidad."""
        return self.add(self.model(**fields), duplicates=self.duplicates, audit=audit)

    def add(
        self,
        model: ModelT,
        *,
        duplicates: dict[str, Callable[[], CommercialRelationshipError]],
        audit: dict[str, Any] | None = None,
    ) -> ModelT:
        self.session.add(model)
        if audit is not None:  # evento en la misma transacción (feature 016)
            audit_events.track_create(self.session, model, **audit)
        commit_or_translate(self.session, duplicates=duplicates)
        self.session.refresh(model)
        end_read(self.session)
        return model

    def load_for_update(self, entity_id: UUID, *, expected_version: int) -> ModelT:
        model = load_for_update(
            self.session, self.model, entity_id, expected_version=expected_version
        )
        audit_events.remember(self.session, model)  # imagen previa (feature 016)
        return model

    def save(
        self,
        model: ModelT,
        *,
        duplicates: dict[str, Callable[[], CommercialRelationshipError]],
        audit: dict[str, Any] | None = None,
    ) -> ModelT:
        if audit is not None:  # solo campos modificados; sin cambios no hay evento (feature 016)
            audit_events.track_update(self.session, model, **audit)
        commit_or_translate(self.session, duplicates=duplicates)
        self.session.refresh(model)
        end_read(self.session)
        return model

    def release(self) -> None:
        """Libera la fila bloqueada sin cambios (`PUT` idéntico)."""
        end_read(self.session)

    # ------------------------------------------- Fase B: bloqueos y marcas (R-04)

    def database_now(self) -> datetime:
        """Instante `now()` de la transacción en curso (R-06: "en vigencia" según la base).

        No cierra la transacción: se usa dentro de una escritura en curso.
        """
        return self.session.scalar(select(func.now()))

    def lock_scope_row(self, model: type, entity_id: UUID) -> None:
        """Bloquea la fila "ámbito" (`SELECT … FOR UPDATE`) antes de cambiar marcas (R-04)."""
        self.session.execute(select(model.id).where(model.id == entity_id).with_for_update())

    def lock_advisory(self, key: str) -> None:
        """Bloqueo consultivo de transacción para ámbitos sin fila propia (R-04)."""
        self.session.execute(
            select(func.pg_advisory_xact_lock(func.hashtextextended(key, 0)))
        )

    def clear_marks(self, flag: str, *conditions: Any, exclude_id: UUID | None, actor: str) -> None:
        """Retira la marca `flag` de los registros `ACTIVE` del ámbito (cambio atómico, DS-04).

        Cada registro desmarcado incrementa su `version` y registra `updated_by` y
        `updated_at` (FR-092, Principio VII). Se envía a la base antes de marcar el
        nuevo registro para que el índice único parcial nunca vea dos marcas.
        """
        statement = select(self.model).where(
            *conditions,
            getattr(self.model, flag).is_(True),
            self.model.status == "ACTIVE",
        )

        if exclude_id is not None:
            statement = statement.where(self.model.id != exclude_id)

        for row in self.session.scalars(statement.with_for_update()):
            setattr(row, flag, False)
            row.updated_by = actor
            row.updated_at = datetime.now(UTC)

        self.session.flush()
