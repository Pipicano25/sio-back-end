"""Marca irreversible de primer uso (FR-076 a FR-080, R-15, DS-18).

- Registro por adopción: lo notifica el servicio consumidor; exige elegibilidad
  solo si falta alguna marca.
- Registro manual: lo hace el administrador; no exige elegibilidad.
- Ambos son idempotentes, bloquean la fila del producto y marcan el producto
  cuando se marca una presentación. Ninguna operación borra la marca.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from product_catalog_service.application import audit_events as audit
from product_catalog_service.application import lifecycle
from product_catalog_service.application.completeness_service import CompletenessService
from product_catalog_service.application.exceptions import (
    NotEligibleForFirstUseError,
    PresentationOfOtherProductError,
    ReferenceNotFoundError,
)
from product_catalog_service.infrastructure.locks import lock_product
from product_catalog_service.infrastructure.models import (
    GlobalProductModel,
    GlobalProductPresentationModel,
)

ADOPTION = "ADOPTION"
MANUAL = "MANUAL"


@dataclass(frozen=True, slots=True)
class FirstUseResult:
    product: GlobalProductModel
    presentation: GlobalProductPresentationModel | None


class FirstUseService:
    """Casos de uso del registro de primer uso."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.completeness = CompletenessService(session)

    def register_adoption(
        self,
        product_id: UUID,
        presentation_id: UUID | None,
        actor: str,
    ) -> FirstUseResult:
        return self._register(product_id, presentation_id, actor, ADOPTION)

    def register_manual(
        self,
        product_id: UUID,
        presentation_id: UUID | None,
        actor: str,
    ) -> FirstUseResult:
        return self._register(product_id, presentation_id, actor, MANUAL)

    def _register(
        self,
        product_id: UUID,
        presentation_id: UUID | None,
        actor: str,
        source: str,
    ) -> FirstUseResult:
        product = lock_product(self.session, product_id)
        presentation = self._presentation(product_id, presentation_id)

        pending = [
            entity
            for entity in (product, presentation)
            if entity is not None and entity.first_used_at is None
        ]

        if not pending:
            self.session.rollback()
            return FirstUseResult(product, presentation)

        if source == ADOPTION:
            self._require_eligible(product, presentation)

        now = lifecycle.utc_now()
        for entity in pending:
            entity.first_used_at = now
            entity.first_used_by = actor
            entity.first_use_source = source
            lifecycle.stamp_update(entity, actor)

        audit.track_update(
            self.session, product, action=audit.REGISTER_PRODUCT_FIRST_USE, entity_type="Product",
            extra_new={
                "origin": "MANUAL" if source == MANUAL else "AUTOMATIC",
                **({"global_product_presentation_id": presentation.id} if presentation in pending else {}),
            },
        )
        self.session.commit()
        return FirstUseResult(product, presentation)

    def _presentation(
        self,
        product_id: UUID,
        presentation_id: UUID | None,
    ) -> GlobalProductPresentationModel | None:
        if presentation_id is None:
            return None

        presentation = self.session.get(GlobalProductPresentationModel, presentation_id)
        if presentation is None:
            raise ReferenceNotFoundError(f"La presentación {presentation_id} no existe.")
        if presentation.global_product_id != product_id:
            raise PresentationOfOtherProductError("La presentación no pertenece al producto indicado.")
        return presentation

    def _require_eligible(
        self,
        product: GlobalProductModel,
        presentation: GlobalProductPresentationModel | None,
    ) -> None:
        completeness = self.completeness.for_product(product.id)

        if not self.completeness.product_eligible(product.status, completeness):
            raise NotEligibleForFirstUseError(
                "El producto no es elegible para nuevas adopciones (inactivo o incompleto)."
            )

        if presentation is not None and not self.completeness.presentation_eligible(
            presentation.status,
            product.status,
            completeness,
        ):
            raise NotEligibleForFirstUseError("La presentación no es elegible para nuevas adopciones.")
