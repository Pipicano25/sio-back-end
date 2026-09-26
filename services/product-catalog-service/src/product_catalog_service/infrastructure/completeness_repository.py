"""Carga de instantáneas para la completitud con consultas por conjuntos (R-14, SC-003)."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import Integer, and_, case, func, select
from sqlalchemy.orm import Session

from product_catalog_service.domain.completeness import (
    VALUE_FIELD_BY_DATA_TYPE,
    ProductSnapshot,
    ValueSnapshot,
)
from product_catalog_service.infrastructure.models import (
    GlobalCategoryAttributeModel,
    GlobalProductAttributeValueModel,
    GlobalProductCategoryModel,
    GlobalProductModel,
    GlobalProductPresentationModel,
    GlobalUnitOfMeasureModel,
    ProductAttributeDefinitionModel,
    ProductAttributeOptionModel,
)

ACTIVE = "ACTIVE"


def load_snapshots(session: Session, product_ids: list[UUID]) -> dict[UUID, ProductSnapshot]:
    """Carga las instantáneas de 1 a 100 productos con cinco consultas fijas."""
    if not product_ids:
        return {}

    products = session.execute(
        select(
            GlobalProductModel.id,
            GlobalProductModel.status,
            GlobalProductModel.product_type,
            GlobalProductModel.canonical_name,
            GlobalProductModel.base_unit_id,
            GlobalUnitOfMeasureModel.id.label("unit_id"),
        )
        .outerjoin(GlobalUnitOfMeasureModel, GlobalUnitOfMeasureModel.id == GlobalProductModel.base_unit_id)
        .where(GlobalProductModel.id.in_(product_ids))
    ).all()

    # 3. Asociaciones producto–categoría ACTIVE (el estado de la categoría no cuenta, RN-15).
    category_counts = {
        row.global_product_id: (row.total, row.primaries)
        for row in session.execute(
            select(
                GlobalProductCategoryModel.global_product_id,
                func.count().label("total"),
                func.sum(case((GlobalProductCategoryModel.is_primary, 1), else_=0)).cast(Integer).label("primaries"),
            )
            .where(
                GlobalProductCategoryModel.global_product_id.in_(product_ids),
                GlobalProductCategoryModel.status == ACTIVE,
            )
            .group_by(GlobalProductCategoryModel.global_product_id)
        )
    }

    # 4. Atributos aplicables y obligatorios de esas categorías (sin herencia).
    applicable: dict[UUID, set[UUID]] = defaultdict(set)
    required: dict[UUID, dict[UUID, str]] = defaultdict(dict)
    for row in session.execute(
        select(
            GlobalProductCategoryModel.global_product_id,
            GlobalCategoryAttributeModel.attribute_definition_id,
            GlobalCategoryAttributeModel.is_required,
            ProductAttributeDefinitionModel.status.label("definition_status"),
            ProductAttributeDefinitionModel.data_type,
        )
        .join(
            GlobalCategoryAttributeModel,
            and_(
                GlobalCategoryAttributeModel.global_category_id == GlobalProductCategoryModel.global_category_id,
                GlobalCategoryAttributeModel.status == ACTIVE,
            ),
        )
        .join(
            ProductAttributeDefinitionModel,
            ProductAttributeDefinitionModel.id == GlobalCategoryAttributeModel.attribute_definition_id,
        )
        .where(
            GlobalProductCategoryModel.global_product_id.in_(product_ids),
            GlobalProductCategoryModel.status == ACTIVE,
        )
    ):
        applicable[row.global_product_id].add(row.attribute_definition_id)
        if row.is_required and row.definition_status == ACTIVE:
            required[row.global_product_id][row.attribute_definition_id] = row.data_type

    # Valores registrados.
    values: dict[UUID, list[ValueSnapshot]] = defaultdict(list)
    value_model = GlobalProductAttributeValueModel
    for row in session.execute(
        select(value_model, ProductAttributeOptionModel.attribute_definition_id.label("option_definition_id"))
        .outerjoin(ProductAttributeOptionModel, ProductAttributeOptionModel.id == value_model.option_id)
        .where(value_model.global_product_id.in_(product_ids))
    ):
        value = row[0]
        filled = next(
            (name for name in VALUE_FIELD_BY_DATA_TYPE.values() if getattr(value, name) is not None),
            None,
        )
        values[value.global_product_id].append(
            ValueSnapshot(
                value_id=value.id,
                definition_id=value.attribute_definition_id,
                filled_field=filled,
                option_definition_id=row.option_definition_id,
            )
        )

    # 6. Presentaciones ACTIVE.
    presentation_counts = dict(
        session.execute(
            select(GlobalProductPresentationModel.global_product_id, func.count())
            .where(
                GlobalProductPresentationModel.global_product_id.in_(product_ids),
                GlobalProductPresentationModel.status == ACTIVE,
            )
            .group_by(GlobalProductPresentationModel.global_product_id)
        ).all()
    )

    snapshots: dict[UUID, ProductSnapshot] = {}
    for row in products:
        total, primaries = category_counts.get(row.id, (0, 0))
        snapshots[row.id] = ProductSnapshot(
            product_id=row.id,
            status=row.status,
            product_type=row.product_type,
            canonical_name=row.canonical_name,
            base_unit_id=row.base_unit_id,
            base_unit_exists=row.unit_id is not None,
            active_category_count=total,
            active_primary_count=primaries or 0,
            required_definitions=dict(required.get(row.id, {})),
            applicable_definition_ids=frozenset(applicable.get(row.id, set())),
            values=tuple(values.get(row.id, [])),
            active_presentation_count=presentation_counts.get(row.id, 0),
        )

    return snapshots
