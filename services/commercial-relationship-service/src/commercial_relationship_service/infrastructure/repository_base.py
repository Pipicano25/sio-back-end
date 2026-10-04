"""Base común de los repositorios SQLAlchemy de las tres entidades.

Las lecturas cierran su transacción implícita al terminar (no retienen
conexiones ni bloqueos mientras se consulta a otros servicios); las escrituras
son transacciones cortas que traducen las violaciones de unicidad por nombre de
restricción (R-08).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from commercial_relationship_service.application.exceptions import CommercialRelationshipError
from commercial_relationship_service.application.pagination import PageResult
from commercial_relationship_service.domain.rules import code_key
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
    ) -> PageResult[ModelT]:
        statement: Select = select(self.model).where(self.model.company_id == company_id)

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
                statement.order_by(self.model.display_name, self.model.id)
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

    def create(self, **fields: Any) -> ModelT:
        """Inserta una fila nueva traduciendo las unicidades de la entidad."""
        return self.add(self.model(**fields), duplicates=self.duplicates)

    def add(self, model: ModelT, *, duplicates: dict[str, Callable[[], CommercialRelationshipError]]) -> ModelT:
        self.session.add(model)
        commit_or_translate(self.session, duplicates=duplicates)
        self.session.refresh(model)
        end_read(self.session)
        return model

    def load_for_update(self, entity_id: UUID, *, expected_version: int) -> ModelT:
        return load_for_update(
            self.session, self.model, entity_id, expected_version=expected_version
        )

    def save(self, model: ModelT, *, duplicates: dict[str, Callable[[], CommercialRelationshipError]]) -> ModelT:
        commit_or_translate(self.session, duplicates=duplicates)
        self.session.refresh(model)
        end_read(self.session)
        return model

    def release(self) -> None:
        """Libera la fila bloqueada sin cambios (`PUT` idéntico)."""
        end_read(self.session)
