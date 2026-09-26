"""Atributos aplicables a un producto (FR-043, DS-02, RN-15)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.infrastructure.models import (
    GlobalCategoryAttributeModel,
    GlobalProductCategoryModel,
    ProductAttributeDefinitionModel,
)

ACTIVE = "ACTIVE"


@dataclass(slots=True)
class ApplicableAttribute:
    definition: ProductAttributeDefinitionModel
    is_required: bool = False
    is_filterable: bool = False
    display_order: int = 0
    category_ids: list[UUID] = field(default_factory=list)


def applicable_for_product(session: Session, product_id: UUID) -> list[ApplicableAttribute]:
    """Unión de asociaciones vigentes de las categorías asignadas directamente.

    Cuentan las asociaciones producto–categoría `ACTIVE` aunque la categoría esté
    `INACTIVE` (RN-15); no se recorren ancestros (DS-02); solo definiciones `ACTIVE`.
    """
    rows = session.execute(
        select(GlobalCategoryAttributeModel, ProductAttributeDefinitionModel)
        .join(
            GlobalProductCategoryModel,
            GlobalProductCategoryModel.global_category_id == GlobalCategoryAttributeModel.global_category_id,
        )
        .join(
            ProductAttributeDefinitionModel,
            ProductAttributeDefinitionModel.id == GlobalCategoryAttributeModel.attribute_definition_id,
        )
        .where(
            GlobalProductCategoryModel.global_product_id == product_id,
            GlobalProductCategoryModel.status == ACTIVE,
            GlobalCategoryAttributeModel.status == ACTIVE,
            ProductAttributeDefinitionModel.status == ACTIVE,
        )
    ).all()

    merged: dict[UUID, ApplicableAttribute] = {}
    for association, definition in rows:
        item = merged.setdefault(
            definition.id,
            ApplicableAttribute(definition=definition, display_order=association.display_order),
        )
        item.is_required = item.is_required or association.is_required
        item.is_filterable = item.is_filterable or association.is_filterable
        item.display_order = min(item.display_order, association.display_order)
        item.category_ids.append(association.global_category_id)

    return sorted(merged.values(), key=lambda item: (item.display_order, item.definition.code))


def applicable_definition_ids(session: Session, product_id: UUID) -> set[UUID]:
    """Definiciones con asociación vigente, sin filtrar por estado de la definición."""
    return set(
        session.execute(
            select(GlobalCategoryAttributeModel.attribute_definition_id)
            .join(
                GlobalProductCategoryModel,
                GlobalProductCategoryModel.global_category_id == GlobalCategoryAttributeModel.global_category_id,
            )
            .where(
                GlobalProductCategoryModel.global_product_id == product_id,
                GlobalProductCategoryModel.status == ACTIVE,
                GlobalCategoryAttributeModel.status == ACTIVE,
            )
        ).scalars()
    )
