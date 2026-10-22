"""Casos de uso de lectura de la spec 022: PC-1 (resumen por lotes) y PC-2 (productos por filtros).

`image_url` solo se construye cuando la ruta pública está habilitada (secreto y URL base pública
configurados; FR-022-99). `has_image` se calcula siempre con la misma regla (FR-022-45, FR-022-46).
"""

from __future__ import annotations

from urllib.parse import urlencode
from uuid import UUID

from sqlalchemy.orm import Session

from product_catalog_service.application.catalog_query_service import BATCH_LIMIT
from product_catalog_service.application.exceptions import BatchLimitExceededError, ValidationError
from product_catalog_service.application.normalization import normalize_identifier_value
from product_catalog_service.config import Settings
from product_catalog_service.domain.image_ref import eligible_image_sha, sign_ref
from product_catalog_service.infrastructure.product_summary_repository import (
    ProductMatchFilters,
    ProductSummaryRepository,
)

PUBLIC_IMAGE_PATH = "/api/v1/public/product-images"


def unique_ids(ids: list[UUID], *, field: str = "ids") -> list[UUID]:
    unique = list(dict.fromkeys(ids))
    if not unique:
        raise ValidationError("Debe enviar al menos un identificador.", field=field)
    if len(unique) > BATCH_LIMIT:
        raise BatchLimitExceededError(f"La consulta por lotes admite como máximo {BATCH_LIMIT} identificadores.")
    return unique


class ProductSummaryService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.repository = ProductSummaryRepository(session)
        self.settings = settings

    def image_url(self, asset_id: UUID, sha256_hex: str) -> str | None:
        if not self.settings.public_images_enabled:
            return None
        ref = sign_ref(asset_id, sha256_hex, self.settings.image_ref_secret)
        return f"{self.settings.public_base_url}{PUBLIC_IMAGE_PATH}?{urlencode({'ref': ref})}"

    def summaries(self, ids: list[UUID]) -> list[dict]:
        requested = unique_ids(ids)
        rows = self.repository.summaries(requested)
        bucket = self.settings.asset_storage_bucket
        items = []

        for product_id in requested:
            product = rows.products.get(product_id)
            if product is None:
                items.append({"id": product_id, "found": False})
                continue

            brand = rows.brands.get(product.global_brand_id) if product.global_brand_id else None
            unit = rows.units.get(product.base_unit_id)
            asset = rows.images.get(product_id)
            sha = eligible_image_sha(asset, bucket) if asset is not None else None

            items.append(
                {
                    "id": product_id,
                    "found": True,
                    "canonical_name": product.canonical_name,
                    "product_type": product.product_type,
                    "status": product.status,
                    "brand": {"id": brand.id, "code": brand.code, "name": brand.name} if brand else None,
                    "base_unit": {"id": unit.id, "code": unit.code, "name": unit.name} if unit else None,
                    "categories": [
                        {"id": category.id, "code": category.code, "name": category.name, "is_primary": link.is_primary}
                        for link, category in rows.categories.get(product_id, [])
                    ],
                    "identifiers": [
                        {
                            "type": identifier.identifier_type,
                            "value": identifier.value,
                            "is_primary": identifier.is_primary,
                            "global_product_presentation_id": identifier.global_product_presentation_id,
                        }
                        for identifier in rows.identifiers.get(product_id, [])
                    ],
                    "has_image": sha is not None,
                    "image_asset_id": asset.id if sha is not None else None,
                    "image_url": self.image_url(asset.id, sha) if sha is not None else None,
                }
            )

        return items

    def _filters(self, values: dict) -> ProductMatchFilters:
        identifier = values.get("identifier")
        return ProductMatchFilters(
            status=values["status"],
            brand_ids=list(dict.fromkeys(values.get("brand_ids") or [])),
            category_ids=list(dict.fromkeys(values.get("category_ids") or [])),
            include_descendants=values.get("include_descendants", False),
            identifier=normalize_identifier_value(identifier) if identifier else None,
            product_type=values.get("product_type"),
            has_image=values.get("has_image"),
        )

    def match_candidates(self, values: dict, candidate_ids: list[UUID]) -> list[UUID]:
        """Modo evaluador: los candidatos que cumplen, en el orden de la solicitud."""
        requested = unique_ids(candidate_ids, field="candidate_ids")
        matched = self.repository.match_candidates(self._filters(values), self.settings.asset_storage_bucket, requested)
        return [candidate for candidate in requested if candidate in matched]

    def match_page(self, values: dict, *, after: tuple[str, UUID] | None, limit: int) -> tuple[list[tuple[UUID, str]], bool]:
        """Modo conductor: productos posteriores a `after` en orden `canonical_name_key, id`."""
        return self.repository.match_page(
            self._filters(values), self.settings.asset_storage_bucket, after=after, limit=limit
        )
