"""Servicio de categorías jerárquicas (FR-020 a FR-024, DS-07)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application.exceptions import (
    HasActiveChildrenError,
    HierarchyCycleError,
    ParentInactiveError,
    ReferenceInactiveError,
    ReferenceNotFoundError,
)
from product_catalog_service.application.lifecycle import ACTIVE, INACTIVE
from product_catalog_service.application.pagination import PageResult, paginate
from product_catalog_service.application.simple_catalog import SimpleCatalogService
from product_catalog_service.domain.hierarchy import would_create_cycle
from product_catalog_service.infrastructure.hierarchy_repository import HierarchyRepository
from product_catalog_service.infrastructure.models import GlobalCategoryModel


class CategoryService(SimpleCatalogService[GlobalCategoryModel]):
    audit_entity = "Category"  # feature 016
    audit_suffix = "CATEGORY"
    model = GlobalCategoryModel
    label = "La categoría"
    code_max_length = 50
    name_max_length = 120

    def __init__(self, session: Session) -> None:
        super().__init__(session)
        self.tree = HierarchyRepository(session, GlobalCategoryModel, "parent_category_id")

    # ------------------------------------------------------------------ lectura

    def children(self, category_id: UUID, *, page: int, page_size: int) -> PageResult:
        self.get(category_id)
        statement = (
            select(GlobalCategoryModel)
            .where(GlobalCategoryModel.parent_category_id == category_id)
            .order_by(GlobalCategoryModel.code)
        )
        return paginate(self.session, statement, page=page, page_size=page_size)

    def descendants(self, category_id: UUID, *, page: int, page_size: int) -> PageResult:
        self.get(category_id)
        statement = self.tree.descendants_statement(category_id).order_by(GlobalCategoryModel.code)
        return paginate(self.session, statement, page=page, page_size=page_size)

    def ancestors(self, category_id: UUID) -> list[GlobalCategoryModel]:
        self.get(category_id)
        return self.tree.ancestors(category_id)

    # ---------------------------------------------------------------- escritura

    def create(self, *, code: str, name: str, actor: str, **fields: Any) -> GlobalCategoryModel:
        self._require_active_parent(fields.get("parent_category_id"))
        return super().create(code=code, name=name, actor=actor, **fields)

    def update(self, entity_id: UUID, *, version: int, name: str, actor: str, **fields: Any):
        new_parent_id = fields.get("parent_category_id")
        current = self.get(entity_id)
        if new_parent_id != current.parent_category_id:
            self._require_active_parent(new_parent_id)
        return super().update(entity_id, version=version, name=name, actor=actor, **fields)

    def before_update(self, entity: GlobalCategoryModel) -> None:
        if would_create_cycle(entity.id, entity.parent_category_id, self._parent_of_excluding(entity)):
            raise HierarchyCycleError(
                "La categoría no puede quedar bajo sí misma ni bajo una descendiente."
            )

    def before_deactivate(self, entity: GlobalCategoryModel) -> None:
        if entity.status == ACTIVE and self.tree.has_active_children(entity.id):
            raise HasActiveChildrenError(
                "Primero deben inactivarse o moverse las categorías hijas activas."
            )

    def before_reactivate(self, entity: GlobalCategoryModel) -> None:
        if entity.parent_category_id is not None:
            parent = self.session.get(GlobalCategoryModel, entity.parent_category_id)
            if parent is not None and parent.status == INACTIVE:
                raise ParentInactiveError("La categoría padre está inactiva.")

    # ---------------------------------------------------------------- utilidades

    def _require_active_parent(self, parent_id: UUID | None) -> None:
        if parent_id is None:
            return

        parent = self.session.get(GlobalCategoryModel, parent_id)
        if parent is None:
            raise ReferenceNotFoundError(f"La categoría padre {parent_id} no existe.")
        if parent.status != ACTIVE:
            raise ReferenceInactiveError("La categoría padre está inactiva.")

    def _parent_of_excluding(self, entity: GlobalCategoryModel):
        """`parent_of` que usa el valor nuevo del nodo que se modifica."""

        def parent_of(node_id: UUID) -> UUID | None:
            if node_id == entity.id:
                return entity.parent_category_id
            return self.tree.parent_of(node_id)

        return parent_of
