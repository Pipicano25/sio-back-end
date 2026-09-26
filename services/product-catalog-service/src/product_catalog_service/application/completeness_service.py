"""Completitud y elegibilidad de productos y presentaciones (FR-032, FR-074, FR-075)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from product_catalog_service.application.exceptions import NotFoundError
from product_catalog_service.domain.completeness import (
    ProductCompleteness,
    evaluate_completeness,
    is_eligible,
    is_presentation_eligible,
)
from product_catalog_service.infrastructure.completeness_repository import load_snapshots


class CompletenessService:
    """Calcula el indicador derivado; nunca lo persiste."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def for_products(self, product_ids: list[UUID]) -> dict[UUID, ProductCompleteness]:
        snapshots = load_snapshots(self.session, list(dict.fromkeys(product_ids)))
        return {product_id: evaluate_completeness(snapshot) for product_id, snapshot in snapshots.items()}

    def for_product(self, product_id: UUID) -> ProductCompleteness:
        result = self.for_products([product_id])
        if product_id not in result:
            raise NotFoundError(f"El producto {product_id} no existe.")
        return result[product_id]

    @staticmethod
    def product_eligible(status: str, completeness: ProductCompleteness) -> bool:
        return is_eligible(status, completeness)

    @staticmethod
    def presentation_eligible(
        presentation_status: str,
        product_status: str,
        completeness: ProductCompleteness,
    ) -> bool:
        return is_presentation_eligible(presentation_status, product_status, completeness)
