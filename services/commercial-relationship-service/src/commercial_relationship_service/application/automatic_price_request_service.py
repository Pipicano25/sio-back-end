"""Entrada de solicitudes de actualización de precio (spec 021: FR-021-19, FR-021-20; DS-05, DS-06; RC-021-5).

Una transacción por solicitud:

1. Comprueba que la presentación y el producto sean de la empresa.
2. Idempotencia por `purchase_detail_id`: la misma solicitud responde lo mismo; con otro contenido, `409
   REQUEST_CONFLICT`. La secuencia repetida con otra línea es `409 SEQUENCE_CONFLICT` (restricción única).
3. Expande una **aplicación por lista** que estaba en modo políticas en `received_at` y copia en ella la política, el
   término y el porcentaje vigentes en ese instante (captura inmutable). Las listas sin políticas en ese instante no
   generan nada (RC-021-6).
4. Audita `RECEIVE_AUTOMATIC_PRICE_REQUEST` con la identidad técnica que entregó y el usuario que recibió.

No calcula precios: lo hace el worker (`automatic_price_application_service`).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from commercial_relationship_service.application import audit_events
from commercial_relationship_service.application.exceptions import (
    PresentationNotFoundError,
    RequestConflictError,
)
from commercial_relationship_service.infrastructure.pricing_repositories import DetailAlreadyReceived
from commercial_relationship_service.infrastructure.models import (
    AutomaticPriceApplicationModel,
    AutomaticPriceUpdateRequestModel,
)

ENTITY = "AutomaticPriceUpdateRequest"
PENDING = "PENDING"


def payload_hash(payload: dict[str, Any]) -> str:
    """SHA-256 del contenido canónico (claves ordenadas, sin espacios, decimales y UUID como texto)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AutomaticPriceRequestService:
    def __init__(self, repository, presentation_repository) -> None:
        self._repository = repository
        self._presentations = presentation_repository

    def submit(self, company_id: UUID, payload: dict[str, Any], *, actor: str):
        """Guarda la solicitud y sus aplicaciones; devuelve `(solicitud, aplicaciones)`."""
        digest = payload_hash(payload)
        existing = self._repository.request_by_detail(payload["purchase_detail_id"])

        if existing is not None:
            if existing.company_id != company_id or existing.payload_hash != digest:
                raise RequestConflictError(field="purchase_detail_id")
            return existing, self._repository.applications_of(existing.id)

        presentation = self._presentations.get(payload["company_product_presentation_id"])
        if (
            presentation is None
            or presentation.company_id != company_id
            or presentation.company_product_id != payload["company_product_id"]
        ):
            raise PresentationNotFoundError(field="company_product_presentation_id")

        received_at = payload["received_at"]
        request = AutomaticPriceUpdateRequestModel(
            id=uuid4(),
            company_id=company_id,
            contract_version=payload["contract_version"],
            purchase_id=payload["purchase_id"],
            purchase_detail_id=payload["purchase_detail_id"],
            branch_id=payload["branch_id"],
            company_product_id=payload["company_product_id"],
            company_product_presentation_id=payload["company_product_presentation_id"],
            sequence=payload["sequence"],
            previous_sequence=payload["previous_sequence"],
            currency_code=payload["currency_code"],
            line_total=payload["line_total"],
            quantity=payload["quantity"],
            previous_purchase_detail_id=payload["previous_purchase_detail_id"],
            previous_line_total=payload["previous_line_total"],
            previous_quantity=payload["previous_quantity"],
            received_at=received_at,
            received_by_user_id=payload["received_by_user_id"],
            payload_hash=digest,
            created_by=actor,
        )
        applications = []
        for price_list_id in self._repository.lists_in_policy_mode(company_id, received_at):
            captured = self._repository.capture(price_list_id, request.company_product_presentation_id, received_at)
            policy_id, term_id, markup = captured if captured else (None, None, None)
            applications.append(
                AutomaticPriceApplicationModel(
                    id=uuid4(),
                    company_id=company_id,
                    request_id=request.id,
                    price_list_id=price_list_id,
                    company_product_presentation_id=request.company_product_presentation_id,
                    sequence=request.sequence,
                    policy_id=policy_id,
                    term_id=term_id,
                    markup_percentage=markup,
                    status=PENDING,
                    created_by=actor,
                    updated_by=actor,
                )
            )

        try:
            self._repository.insert_request(
                request,
                applications,
                audit=audit_events.spec(
                    audit_events.RECEIVE_AUTOMATIC_PRICE_REQUEST,
                    ENTITY,
                    company_id,
                    branch_id=request.branch_id,
                    extra_new={"application_ids": [application.id for application in applications]},
                ),
            )
        except DetailAlreadyReceived:
            self._repository.rollback()
            return self.submit(company_id, payload, actor=actor)  # la otra entrega ganó: misma respuesta o conflicto
        except Exception:
            self._repository.rollback()
            raise
        return request, applications
