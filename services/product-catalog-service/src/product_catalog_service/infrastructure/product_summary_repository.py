"""Lecturas de la spec 022: resumen del catálogo por lotes (PC-1) y productos por filtros (PC-2).

Solo lectura. PC-1 ejecuta un número fijo de consultas por lote, sin importar cuántos productos
pida (sin N+1). PC-2 ordena por `canonical_name_key, id`, y la comparación *keyset* de filas la hace
PostgreSQL, con la misma intercalación del `ORDER BY`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import ColumnElement, exists, not_, select, tuple_
from sqlalchemy.orm import Session

from product_catalog_service.domain.image_ref import ALLOWED_IMAGE_TYPES
from product_catalog_service.infrastructure.hierarchy_repository import HierarchyRepository
from product_catalog_service.infrastructure.models import (
    GlobalBrandModel,
    GlobalCategoryModel,
    GlobalProductCategoryModel,
    GlobalProductIdentifierModel,
    GlobalProductModel,
    GlobalUnitOfMeasureModel,
    ProductAssetModel,
)
from product_catalog_service.infrastructure.product_query_repository import identifier_match_condition

ACTIVE = "ACTIVE"
ALL = "ALL"


@dataclass(slots=True)
class ProductMatchFilters:
    """Filtros de PC-2, ya validados."""

    status: str = ACTIVE
    brand_ids: list[UUID] = field(default_factory=list)
    category_ids: list[UUID] = field(default_factory=list)
    include_descendants: bool = False
    identifier: str | None = None
    product_type: str | None = None
    has_image: bool | None = None


@dataclass(slots=True)
class SummaryRows:
    """Filas de un lote de PC-1, agrupadas por producto."""

    products: dict[UUID, GlobalProductModel]
    brands: dict[UUID, GlobalBrandModel]
    units: dict[UUID, GlobalUnitOfMeasureModel]
    categories: dict[UUID, list[tuple[GlobalProductCategoryModel, GlobalCategoryModel]]]
    identifiers: dict[UUID, list[GlobalProductIdentifierModel]]
    images: dict[UUID, ProductAssetModel]


def eligible_image_condition(bucket: str) -> ColumnElement:
    """`EXISTS` de la imagen principal apta (FR-022-46), la misma regla de `eligible_image_sha`."""
    asset = ProductAssetModel
    return exists().where(
        asset.global_product_id == GlobalProductModel.id,
        asset.asset_type == "IMAGE",
        asset.status == ACTIVE,
        asset.is_primary.is_(True),
        asset.mime_type.in_(sorted(ALLOWED_IMAGE_TYPES)),
        asset.storage_uri.like(f"s3://{bucket}/%"),
        asset.storage_uri.op("~")("(^|[^0-9a-f])[0-9a-f]{64}([^0-9a-f]|$)"),
    )


class ProductSummaryRepository:
    """Consultas de solo lectura de PC-1 y PC-2."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ------------------------------------------------------------------ PC-1

    def summaries(self, ids: list[UUID]) -> SummaryRows:
        products = {
            row.id: row
            for row in self.session.scalars(select(GlobalProductModel).where(GlobalProductModel.id.in_(ids)))
        }
        brand_ids = {p.global_brand_id for p in products.values() if p.global_brand_id is not None}
        unit_ids = {p.base_unit_id for p in products.values()}
        found = list(products)

        brands = (
            {row.id: row for row in self.session.scalars(select(GlobalBrandModel).where(GlobalBrandModel.id.in_(brand_ids)))}
            if brand_ids
            else {}
        )
        units = (
            {
                row.id: row
                for row in self.session.scalars(
                    select(GlobalUnitOfMeasureModel).where(GlobalUnitOfMeasureModel.id.in_(unit_ids))
                )
            }
            if unit_ids
            else {}
        )

        categories: dict[UUID, list] = defaultdict(list)
        identifiers: dict[UUID, list] = defaultdict(list)
        images: dict[UUID, ProductAssetModel] = {}

        if found:
            association = GlobalProductCategoryModel
            for link, category in self.session.execute(
                select(association, GlobalCategoryModel)
                .join(GlobalCategoryModel, GlobalCategoryModel.id == association.global_category_id)
                .where(association.global_product_id.in_(found), association.status == ACTIVE)
                .order_by(association.global_product_id, association.is_primary.desc(), GlobalCategoryModel.code)
            ):
                categories[link.global_product_id].append((link, category))

            identifier = GlobalProductIdentifierModel
            for row in self.session.scalars(
                select(identifier)
                .where(identifier.global_product_id.in_(found), identifier.status == ACTIVE)
                .order_by(identifier.global_product_id, identifier.is_primary.desc(), identifier.identifier_type,
                          identifier.value)
            ):
                identifiers[row.global_product_id].append(row)

            asset = ProductAssetModel
            for row in self.session.scalars(
                select(asset).where(
                    asset.global_product_id.in_(found),
                    asset.asset_type == "IMAGE",
                    asset.status == ACTIVE,
                    asset.is_primary.is_(True),
                )
            ):
                images[row.global_product_id] = row

        return SummaryRows(products, brands, units, dict(categories), dict(identifiers), images)

    # ------------------------------------------------------------------ PC-2

    def _match_statement(self, filters: ProductMatchFilters, bucket: str):
        product = GlobalProductModel
        statement = select(product.id, product.canonical_name_key)

        if filters.status != ALL:
            statement = statement.where(product.status == filters.status)

        if filters.brand_ids:
            statement = statement.where(product.global_brand_id.in_(filters.brand_ids))

        if filters.category_ids:
            category_ids: set[UUID] = set()
            hierarchy = HierarchyRepository(self.session, GlobalCategoryModel, "parent_category_id")
            for category_id in filters.category_ids:
                category_ids.update(
                    hierarchy.descendant_ids_including(category_id) if filters.include_descendants else [category_id]
                )
            statement = statement.where(
                exists().where(
                    GlobalProductCategoryModel.global_product_id == product.id,
                    GlobalProductCategoryModel.status == ACTIVE,
                    GlobalProductCategoryModel.global_category_id.in_(category_ids),
                )
            )

        if filters.identifier:
            statement = statement.where(
                exists().where(
                    GlobalProductIdentifierModel.global_product_id == product.id,
                    GlobalProductIdentifierModel.status == ACTIVE,
                    identifier_match_condition(filters.identifier, include_other=True),
                )
            )

        if filters.product_type is not None:
            statement = statement.where(product.product_type == filters.product_type)

        if filters.has_image is not None:
            condition = eligible_image_condition(bucket)
            statement = statement.where(condition if filters.has_image else not_(condition))

        return statement

    def match_candidates(self, filters: ProductMatchFilters, bucket: str, candidate_ids: list[UUID]) -> set[UUID]:
        """Modo evaluador: los candidatos que cumplen los filtros."""
        statement = self._match_statement(filters, bucket).where(GlobalProductModel.id.in_(candidate_ids))
        return {row.id for row in self.session.execute(statement)}

    def match_page(
        self,
        filters: ProductMatchFilters,
        bucket: str,
        *,
        after: tuple[str, UUID] | None,
        limit: int,
    ) -> tuple[list[tuple[UUID, str]], bool]:
        """Modo conductor: `(id, canonical_name_key)` en orden estable, posteriores a `after`."""
        product = GlobalProductModel
        statement = self._match_statement(filters, bucket)

        if after is not None:
            statement = statement.where(tuple_(product.canonical_name_key, product.id) > tuple_(after[0], after[1]))

        rows = list(
            self.session.execute(statement.order_by(product.canonical_name_key, product.id).limit(limit + 1))
        )
        page = [(row.id, row.canonical_name_key) for row in rows[:limit]]
        return page, len(rows) > limit
