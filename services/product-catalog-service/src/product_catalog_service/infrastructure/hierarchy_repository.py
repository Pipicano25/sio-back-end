"""Consultas jerárquicas con CTE recursivas (categorías y grupos, R-11)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, literal, select
from sqlalchemy.orm import Session, aliased

from product_catalog_service.application.lifecycle import ACTIVE


class HierarchyRepository:
    """Consultas de árbol sobre un modelo con columna padre autorreferenciada."""

    def __init__(self, session: Session, model, parent_column_name: str) -> None:
        self.session = session
        self.model = model
        self.parent_column_name = parent_column_name

    @property
    def _parent(self):
        return getattr(self.model, self.parent_column_name)

    def parent_of(self, node_id: UUID) -> UUID | None:
        return self.session.execute(
            select(self._parent).where(self.model.id == node_id)
        ).scalar_one_or_none()

    def ancestors(self, node_id: UUID) -> list:
        """Ancestros ordenados de la raíz al nodo (incluye el nodo)."""
        base = select(self.model.id, self._parent.label("parent_id"), literal(0).label("depth")).where(
            self.model.id == node_id
        ).cte("ancestors", recursive=True)
        parent_alias = aliased(self.model)
        recursive = base.union_all(
            select(
                parent_alias.id,
                getattr(parent_alias, self.parent_column_name),
                (base.c.depth + 1),
            ).where(parent_alias.id == base.c.parent_id)
        )
        rows = self.session.execute(select(recursive.c.id, recursive.c.depth)).all()
        ordered_ids = [row.id for row in sorted(rows, key=lambda row: row.depth, reverse=True)]
        entities = {
            entity.id: entity
            for entity in self.session.execute(
                select(self.model).where(self.model.id.in_(ordered_ids))
            ).scalars()
        }
        return [entities[entity_id] for entity_id in ordered_ids]

    def descendants_statement(self, node_id: UUID) -> Select:
        """Consulta de descendientes (sin incluir el nodo)."""
        base = select(self.model.id).where(self._parent == node_id).cte(
            "descendants", recursive=True
        )
        child_alias = aliased(self.model)
        recursive = base.union_all(
            select(child_alias.id).where(
                getattr(child_alias, self.parent_column_name) == base.c.id
            )
        )
        return select(self.model).where(self.model.id.in_(select(recursive.c.id)))

    def descendant_ids_including(self, node_id: UUID) -> list[UUID]:
        ids = list(
            self.session.execute(
                self.descendants_statement(node_id).with_only_columns(self.model.id)
            ).scalars()
        )
        return [node_id, *ids]

    def has_active_children(self, node_id: UUID) -> bool:
        return (
            self.session.execute(
                select(self.model.id).where(
                    self._parent == node_id,
                    self.model.status == ACTIVE,
                )
            ).first()
            is not None
        )

