"""Consultas de lectura del catálogo: búsqueda, detalle y lotes (FR-033, FR-058, FR-070, FR-071)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import Select, and_, exists, or_, select
from sqlalchemy.orm import Session

from product_catalog_service.domain.gtin import GTIN_FAMILY, gtin_canonical, has_gtin_shape
from product_catalog_service.infrastructure.hierarchy_repository import HierarchyRepository
from product_catalog_service.infrastructure.models import (
    GlobalCategoryAttributeModel,
    GlobalCategoryModel,
    GlobalProductAttributeValueModel,
    GlobalProductCategoryModel,
    GlobalProductGroupAssignmentModel,
    GlobalProductIdentifierModel,
    GlobalProductModel,
    GlobalProductPresentationModel,
    GlobalUnitOfMeasureModel,
    ProductAssetModel,
)
from product_catalog_service.infrastructure.query_helpers import apply_common_filters

ACTIVE = "ACTIVE"


@dataclass(frozen=True, slots=True)
class AttributeCondition:
    """Condición de búsqueda por valor de atributo ya tipada."""

    definition_id: UUID
    column: str
    value: object


@dataclass(slots=True)
class ProductSearchFilters:
    status: str | None = None
    search: str | None = None
    category_id: UUID | None = None
    include_descendants: bool = False
    brand_id: UUID | None = None
    manufacturer_organization_id: UUID | None = None
    group_id: UUID | None = None
    identifier: str | None = None
    attribute_conditions: list[AttributeCondition] = field(default_factory=list)


def identifier_match_condition(value: str, *, include_other: bool = False):
    """Condición de identificador por valor normalizado.

    Siempre considera la familia GTIN (forma canónica) y `BARCODE`, que son únicos
    en todo el catálogo. Con `include_other` también considera `OTHER`, que solo es
    único dentro de su producto y puede coincidir en varios (búsqueda, FR-071).
    """
    conditions = [
        and_(
            GlobalProductIdentifierModel.identifier_type == "BARCODE",
            GlobalProductIdentifierModel.value == value,
        )
    ]
    if include_other:
        conditions.append(
            and_(
                GlobalProductIdentifierModel.identifier_type == "OTHER",
                GlobalProductIdentifierModel.value == value,
            )
        )
    if has_gtin_shape(value):
        conditions.append(
            and_(
                GlobalProductIdentifierModel.identifier_type.in_(sorted(GTIN_FAMILY)),
                GlobalProductIdentifierModel.canonical_value == gtin_canonical(value),
            )
        )
    return or_(*conditions)


class ProductQueryRepository:
    """Lecturas compuestas sobre productos y sus dependientes."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ---------------------------------------------------------------- búsqueda

    def search_statement(self, filters: ProductSearchFilters) -> Select:
        product = GlobalProductModel
        statement = apply_common_filters(
            select(product),
            product,
            status=filters.status,
            search=filters.search,
            search_column=product.canonical_name_key,
        )

        if filters.category_id is not None:
            category_ids = (
                HierarchyRepository(self.session, GlobalCategoryModel, "parent_category_id")
                .descendant_ids_including(filters.category_id)
                if filters.include_descendants
                else [filters.category_id]
            )
            statement = statement.where(
                exists().where(
                    GlobalProductCategoryModel.global_product_id == product.id,
                    GlobalProductCategoryModel.status == ACTIVE,
                    GlobalProductCategoryModel.global_category_id.in_(category_ids),
                )
            )

        if filters.brand_id is not None:
            statement = statement.where(product.global_brand_id == filters.brand_id)

        if filters.manufacturer_organization_id is not None:
            statement = statement.where(
                product.manufacturer_organization_id == filters.manufacturer_organization_id
            )

        if filters.group_id is not None:
            statement = statement.where(
                exists().where(
                    GlobalProductGroupAssignmentModel.global_product_id == product.id,
                    GlobalProductGroupAssignmentModel.global_product_group_id == filters.group_id,
                    GlobalProductGroupAssignmentModel.status == ACTIVE,
                )
            )

        if filters.identifier:
            statement = statement.where(
                exists().where(
                    GlobalProductIdentifierModel.global_product_id == product.id,
                    identifier_match_condition(filters.identifier, include_other=True),
                )
            )

        for condition in filters.attribute_conditions:
            value_column = getattr(GlobalProductAttributeValueModel, condition.column)
            statement = statement.where(
                exists().where(
                    GlobalProductAttributeValueModel.global_product_id == product.id,
                    GlobalProductAttributeValueModel.attribute_definition_id == condition.definition_id,
                    value_column == condition.value,
                ),
                # El atributo debe ser filtrable en alguna categoría vigente del producto.
                exists().where(
                    GlobalProductCategoryModel.global_product_id == product.id,
                    GlobalProductCategoryModel.status == ACTIVE,
                    GlobalCategoryAttributeModel.global_category_id
                    == GlobalProductCategoryModel.global_category_id,
                    GlobalCategoryAttributeModel.attribute_definition_id == condition.definition_id,
                    GlobalCategoryAttributeModel.status == ACTIVE,
                    GlobalCategoryAttributeModel.is_filterable.is_(True),
                ),
            )

        return statement.order_by(product.canonical_name_key, product.id)

    # ----------------------------------------------------------------- detalle

    def detail(self, product_id: UUID) -> dict[str, list]:
        def active(model, *order):
            return list(
                self.session.execute(
                    select(model)
                    .where(model.global_product_id == product_id, model.status == ACTIVE)
                    .order_by(*order)
                ).scalars()
            )

        return {
            "categories": active(
                GlobalProductCategoryModel,
                GlobalProductCategoryModel.is_primary.desc(),
                GlobalProductCategoryModel.created_at,
            ),
            "presentations": active(
                GlobalProductPresentationModel,
                GlobalProductPresentationModel.display_order,
                GlobalProductPresentationModel.code,
            ),
            "identifiers": active(
                GlobalProductIdentifierModel,
                GlobalProductIdentifierModel.identifier_type,
                GlobalProductIdentifierModel.value,
            ),
            "attribute_values": list(
                self.session.execute(
                    select(GlobalProductAttributeValueModel)
                    .where(GlobalProductAttributeValueModel.global_product_id == product_id)
                    .order_by(GlobalProductAttributeValueModel.created_at)
                ).scalars()
            ),
            "group_assignments": active(
                GlobalProductGroupAssignmentModel,
                GlobalProductGroupAssignmentModel.created_at,
            ),
            "assets": active(ProductAssetModel, ProductAssetModel.asset_type, ProductAssetModel.created_at),
        }

    # -------------------------------------------------------------- por código

    def find_by_scanned_value(self, value: str) -> GlobalProductIdentifierModel | None:
        return self.session.execute(
            select(GlobalProductIdentifierModel)
            .where(identifier_match_condition(value))
            .order_by(GlobalProductIdentifierModel.status, GlobalProductIdentifierModel.created_at)
            .limit(1)
        ).scalar_one_or_none()

    # ------------------------------------------------------------------- lotes

    def products_by_ids(self, ids: list[UUID]) -> dict[UUID, GlobalProductModel]:
        return {
            item.id: item
            for item in self.session.execute(
                select(GlobalProductModel).where(GlobalProductModel.id.in_(ids))
            ).scalars()
        }

    def presentations_by_ids(self, ids: list[UUID]) -> dict[UUID, GlobalProductPresentationModel]:
        return {
            item.id: item
            for item in self.session.execute(
                select(GlobalProductPresentationModel).where(GlobalProductPresentationModel.id.in_(ids))
            ).scalars()
        }

    def units_by_ids(self, ids: list[UUID]) -> dict[UUID, GlobalUnitOfMeasureModel]:
        return {
            item.id: item
            for item in self.session.execute(
                select(GlobalUnitOfMeasureModel).where(GlobalUnitOfMeasureModel.id.in_(ids))
            ).scalars()
        }
