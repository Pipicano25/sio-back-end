"""Consultas del catálogo para usuarios y servicios consumidores (US4)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from product_catalog_service.application.completeness_service import CompletenessService
from product_catalog_service.application.exceptions import (
    AttributeNotFilterableError,
    BatchLimitExceededError,
    NotFoundError,
    ValidationError,
)
from product_catalog_service.application.image_urls import asset_image_url, signed_image_url
from product_catalog_service.application.normalization import normalize_identifier_value
from product_catalog_service.application.pagination import PageResult, paginate
from product_catalog_service.config import Settings
from product_catalog_service.domain.completeness import ProductCompleteness
from product_catalog_service.domain.image_ref import eligible_image_sha
from product_catalog_service.infrastructure.models import (
    GlobalCategoryAttributeModel,
    GlobalProductIdentifierModel,
    GlobalProductModel,
    GlobalProductPresentationModel,
    ProductAttributeDefinitionModel,
    ProductAttributeOptionModel,
)
from product_catalog_service.infrastructure.product_query_repository import (
    AttributeCondition,
    ProductQueryRepository,
    ProductSearchFilters,
)

BATCH_LIMIT = 100
ACTIVE = "ACTIVE"


@dataclass(frozen=True, slots=True)
class IdentifierLookup:
    identifier: GlobalProductIdentifierModel
    product: GlobalProductModel
    presentation: GlobalProductPresentationModel | None
    is_current: bool


class CatalogQueryService:
    """Búsqueda, detalle, lotes y búsqueda por código."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ProductQueryRepository(session)
        self.completeness = CompletenessService(session)

    # ---------------------------------------------------------------- búsqueda

    def search(
        self,
        filters: ProductSearchFilters,
        raw_attribute_filters: list[str],
        *,
        page: int,
        page_size: int,
    ) -> PageResult:
        filters.attribute_conditions = [self._parse_attribute_filter(raw) for raw in raw_attribute_filters]
        if filters.identifier:
            filters.identifier = normalize_identifier_value(filters.identifier)
        return paginate(
            self.session,
            self.repository.search_statement(filters),
            page=page,
            page_size=page_size,
        )

    def _parse_attribute_filter(self, raw: str) -> AttributeCondition:
        code, separator, raw_value = raw.partition(":")
        if not separator or not code.strip() or raw_value == "":
            raise ValidationError(
                "Cada filtro de atributo debe tener la forma CODIGO:valor.",
                field="attribute_filters",
            )

        definition = self.session.execute(
            select(ProductAttributeDefinitionModel).where(
                ProductAttributeDefinitionModel.code == code.strip().upper()
            )
        ).scalar_one_or_none()

        filterable = definition is not None and self.session.execute(
            select(GlobalCategoryAttributeModel.id).where(
                GlobalCategoryAttributeModel.attribute_definition_id == definition.id,
                GlobalCategoryAttributeModel.status == ACTIVE,
                GlobalCategoryAttributeModel.is_filterable.is_(True),
            )
        ).first() is not None

        if not filterable:
            raise AttributeNotFilterableError(
                f"El atributo {code.strip().upper()} no es filtrable en ninguna categoría vigente."
            )

        return AttributeCondition(
            definition_id=definition.id,
            column=_value_column(definition.data_type),
            value=self._typed_value(definition, raw_value),
        )

    def _typed_value(self, definition: ProductAttributeDefinitionModel, raw: str):
        data_type = definition.data_type
        try:
            if data_type == "TEXT":
                return raw.strip()
            if data_type == "INTEGER":
                return int(raw)
            if data_type == "DECIMAL":
                return Decimal(raw)
            if data_type == "BOOLEAN":
                lowered = raw.strip().lower()
                if lowered not in {"true", "false"}:
                    raise ValueError(raw)
                return lowered == "true"
            if data_type == "DATE":
                return date.fromisoformat(raw.strip())
        except (ValueError, InvalidOperation):
            raise ValidationError(
                f"El valor {raw!r} no es válido para el atributo {definition.code}.",
                field="attribute_filters",
            ) from None

        option_id = self.session.execute(
            select(ProductAttributeOptionModel.id).where(
                ProductAttributeOptionModel.attribute_definition_id == definition.id,
                ProductAttributeOptionModel.code == raw.strip().upper(),
            )
        ).scalar_one_or_none()
        if option_id is None:
            raise ValidationError(
                f"La opción {raw!r} no existe en el atributo {definition.code}.",
                field="attribute_filters",
            )
        return option_id

    # ----------------------------------------------------------------- detalle

    def detail(self, product_id: UUID, completeness: ProductCompleteness) -> dict[str, list]:
        sections = self.repository.detail(product_id)
        out_of_classification = set(completeness.out_of_classification_value_ids)
        sections["out_of_classification_value_ids"] = out_of_classification
        return sections

    # ------------------------------------------------------------------- lotes

    @staticmethod
    def _unique_ids(ids: list[UUID]) -> list[UUID]:
        unique = list(dict.fromkeys(ids))
        if not unique:
            raise ValidationError("Debe enviar al menos un identificador.", field="ids")
        if len(unique) > BATCH_LIMIT:
            raise BatchLimitExceededError(
                f"La consulta por lotes admite como máximo {BATCH_LIMIT} identificadores."
            )
        return unique

    def lookup_products(self, ids: list[UUID]) -> list[dict]:
        unique = self._unique_ids(ids)
        products = self.repository.products_by_ids(unique)
        completeness = self.completeness.for_products(list(products))
        items = []
        for product_id in unique:
            product = products.get(product_id)
            if product is None:
                items.append({"id": product_id, "found": False})
                continue
            result = completeness[product_id]
            items.append(
                {
                    "id": product_id,
                    "found": True,
                    "status": product.status,
                    "is_complete": result.is_complete,
                    "eligible_for_adoption": self.completeness.product_eligible(product.status, result),
                    "first_used_at": product.first_used_at,
                }
            )
        return items

    def lookup_presentations(
        self, ids: list[UUID], *, settings: Settings | None = None, include_images: bool = False
    ) -> list[dict]:
        """PC-3. Con `settings`, cada presentación encontrada trae su imagen (spec 024, FR-024-37): una sola
        consulta de imágenes por lote; `images` solo con `include_images`."""
        unique = self._unique_ids(ids)
        presentations = self.repository.presentations_by_ids(unique)
        images = self.repository.presentation_images(list(presentations)) if settings is not None else {}
        product_ids = list({item.global_product_id for item in presentations.values()})
        products = self.repository.products_by_ids(product_ids)
        completeness = self.completeness.for_products(product_ids)
        items = []
        for presentation_id in unique:
            presentation = presentations.get(presentation_id)
            if presentation is None:
                items.append({"id": presentation_id, "found": False})
                continue
            product = products[presentation.global_product_id]
            items.append(
                {
                    "id": presentation_id,
                    "found": True,
                    "global_product_id": presentation.global_product_id,
                    "code": presentation.code,
                    "name": presentation.name,
                    "status": presentation.status,
                    "eligible_for_adoption": self.completeness.presentation_eligible(
                        presentation.status,
                        product.status,
                        completeness[product.id],
                    ),
                    "base_quantity": presentation.base_quantity,
                    "first_used_at": presentation.first_used_at,
                    **(self._image_fields(images.get(presentation_id, []), settings, include_images)
                       if settings is not None else {}),
                }
            )
        return items

    @staticmethod
    def _image_fields(assets: list, settings: Settings, include_images: bool) -> dict:
        primary = next((asset for asset in assets if asset.is_primary), None)
        sha = eligible_image_sha(primary, settings.asset_storage_bucket) if primary is not None else None
        fields = {
            "has_image": sha is not None,
            "image_asset_id": primary.id if sha is not None else None,
            "image_url": signed_image_url(settings, primary.id, sha) if sha is not None else None,
        }
        if include_images:
            fields["images"] = [
                {"asset_id": asset.id, "image_url": asset_image_url(settings, asset), "is_primary": asset.is_primary}
                for asset in assets
            ]
        return fields

    def lookup_units(self, ids: list[UUID]) -> list[dict]:
        unique = self._unique_ids(ids)
        units = self.repository.units_by_ids(unique)
        items = []
        for unit_id in unique:
            unit = units.get(unit_id)
            if unit is None:
                items.append({"id": unit_id, "found": False})
                continue
            items.append(
                {
                    "id": unit_id,
                    "found": True,
                    "status": unit.status,
                    "measurement_type": unit.measurement_type,
                    "allows_decimals": unit.allows_decimals,
                    "code": unit.code,
                    "name": unit.name,
                }
            )
        return items

    # -------------------------------------------------------------- por código

    def by_identifier(self, raw_value: str) -> IdentifierLookup:
        value = normalize_identifier_value(raw_value)
        identifier = self.repository.find_by_scanned_value(value)
        if identifier is None:
            raise NotFoundError(f"No existe un producto con el código {value}.")

        product = self.session.get(GlobalProductModel, identifier.global_product_id)
        presentation = (
            self.session.get(GlobalProductPresentationModel, identifier.global_product_presentation_id)
            if identifier.global_product_presentation_id is not None
            else None
        )
        is_current = (
            identifier.status == ACTIVE
            and product.status == ACTIVE
            and (presentation is None or presentation.status == ACTIVE)
        )
        return IdentifierLookup(identifier, product, presentation, is_current)


def _value_column(data_type: str) -> str:
    return {
        "TEXT": "text_value",
        "INTEGER": "integer_value",
        "DECIMAL": "decimal_value",
        "BOOLEAN": "boolean_value",
        "DATE": "date_value",
        "OPTION": "option_id",
    }[data_type]
