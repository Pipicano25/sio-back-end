"""Atributos por categoría (FR-041 a FR-043, DS-02)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application import lifecycle
from product_catalog_service.application.exceptions import (
    DuplicateAssociationError,
    NotFoundError,
    ReferenceInactiveError,
    ReferenceNotFoundError,
)
from product_catalog_service.infrastructure.category_attribute_repository import (
    ApplicableAttribute,
    applicable_for_product,
)
from product_catalog_service.infrastructure.locks import lock_row
from product_catalog_service.infrastructure.models import (
    GlobalCategoryAttributeModel,
    GlobalCategoryModel,
    GlobalProductModel,
    ProductAttributeDefinitionModel,
)

ACTIVE = lifecycle.ACTIVE


class CategoryAttributeService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, category_id: UUID, status: str | None = None) -> list[GlobalCategoryAttributeModel]:
        if self.session.get(GlobalCategoryModel, category_id) is None:
            raise NotFoundError(f"La categoría {category_id} no existe.")
        statement = select(GlobalCategoryAttributeModel).where(
            GlobalCategoryAttributeModel.global_category_id == category_id
        )
        if status is not None:
            statement = statement.where(GlobalCategoryAttributeModel.status == status)
        return list(
            self.session.execute(
                statement.order_by(GlobalCategoryAttributeModel.display_order, GlobalCategoryAttributeModel.created_at)
            ).scalars()
        )

    def associate(
        self,
        category_id: UUID,
        *,
        attribute_definition_id: UUID,
        is_required: bool,
        is_filterable: bool,
        display_order: int,
        actor: str,
    ) -> tuple[GlobalCategoryAttributeModel, bool]:
        category = lock_row(self.session, GlobalCategoryModel, category_id, label="La categoría")
        self._require_active_references(category, attribute_definition_id)

        association = self.session.execute(
            select(GlobalCategoryAttributeModel).where(
                GlobalCategoryAttributeModel.global_category_id == category_id,
                GlobalCategoryAttributeModel.attribute_definition_id == attribute_definition_id,
            )
        ).scalar_one_or_none()

        if association is not None and association.status == ACTIVE:
            raise DuplicateAssociationError("La categoría ya usa esa definición de atributo.")

        created = association is None
        if association is None:
            association = GlobalCategoryAttributeModel(
                global_category_id=category_id,
                attribute_definition_id=attribute_definition_id,
                status=ACTIVE,
            )
            lifecycle.stamp_create(association, actor)
            self.session.add(association)
        else:
            association.status = ACTIVE
            lifecycle.stamp_update(association, actor)

        association.is_required = is_required
        association.is_filterable = is_filterable
        association.display_order = display_order
        self.session.commit()
        return association, created

    def update(
        self,
        category_id: UUID,
        association_id: UUID,
        *,
        version: int,
        is_required: bool,
        is_filterable: bool,
        display_order: int,
        actor: str,
    ) -> GlobalCategoryAttributeModel:
        association = self._association(category_id, association_id)
        lifecycle.check_version(association, version)
        association.is_required = is_required
        association.is_filterable = is_filterable
        association.display_order = display_order
        lifecycle.stamp_update(association, actor)
        self.session.commit()
        return association

    def deactivate(self, category_id: UUID, association_id: UUID, *, version: int, actor: str):
        association = self._association(category_id, association_id)
        lifecycle.deactivate(association, version, actor)
        self.session.commit()
        return association

    def reactivate(self, category_id: UUID, association_id: UUID, *, version: int, actor: str):
        association = self._association(category_id, association_id)
        category = self.session.get(GlobalCategoryModel, category_id)
        self._require_active_references(category, association.attribute_definition_id)
        lifecycle.reactivate(association, version, actor)
        self.session.commit()
        return association

    def applicable_attributes(self, product_id: UUID) -> list[ApplicableAttribute]:
        if self.session.get(GlobalProductModel, product_id) is None:
            raise NotFoundError(f"El producto {product_id} no existe.")
        return applicable_for_product(self.session, product_id)

    # ---------------------------------------------------------------- utilidades

    def _association(self, category_id: UUID, association_id: UUID) -> GlobalCategoryAttributeModel:
        association = lock_row(
            self.session, GlobalCategoryAttributeModel, association_id, label="La asociación"
        )
        if association.global_category_id != category_id:
            raise NotFoundError(f"La asociación {association_id} no pertenece a la categoría.")
        return association

    def _require_active_references(self, category: GlobalCategoryModel, definition_id: UUID) -> None:
        if category.status != ACTIVE:
            raise ReferenceInactiveError("La categoría está inactiva.")

        definition = self.session.get(ProductAttributeDefinitionModel, definition_id)
        if definition is None:
            raise ReferenceNotFoundError(f"La definición de atributo {definition_id} no existe.")
        if definition.status != ACTIVE:
            raise ReferenceInactiveError("La definición de atributo está inactiva.")
