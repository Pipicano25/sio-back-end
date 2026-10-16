"""Esquemas de las actualizaciones automáticas de precio (spec 021, `contracts/price-update-request.md` y §3–§4).

El cuerpo de la ruta A1 es el contrato v1 que entrega Purchase: solo hechos, con importes como decimales en texto.
Las respuestas de A2 y A3 presentan costos y porcentajes, por eso solo las consultan administradores y supervisores
(FR-021-32a); los importes salen como texto decimal: precios con los decimales de la moneda de la lista,
porcentajes con 4 y costos de trazabilidad sin ceros sobrantes.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field, model_validator

from commercial_relationship_service.api.schemas.common import StrictModel, Version, _strip

CURRENCY = re.compile(r"^[A-Z]{3}$")


class PriceUpdateRequestIn(StrictModel):
    """Contrato v1 de la solicitud por recepción (una línea de compra)."""

    contract_version: Literal[1]
    purchase_detail_id: UUID
    purchase_id: UUID
    branch_id: UUID
    company_product_id: UUID
    company_product_presentation_id: UUID
    sequence: int = Field(gt=0)
    previous_sequence: int | None = None
    currency_code: str
    line_total: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    quantity: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    previous_purchase_detail_id: UUID | None = None
    previous_line_total: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    previous_quantity: Decimal | None = Field(default=None, gt=0, max_digits=18, decimal_places=4)
    received_at: AwareDatetime
    received_by_user_id: UUID

    @model_validator(mode="after")
    def _consistent(self) -> PriceUpdateRequestIn:
        if self.previous_sequence is not None and self.previous_sequence != self.sequence - 1:
            raise ValueError("previous_sequence debe ser sequence - 1 o nulo.")
        if self.previous_sequence is None and self.sequence != 1:
            raise ValueError("Solo la primera solicitud de la serie (sequence = 1) no tiene previous_sequence.")
        if (self.previous_line_total is None) != (self.previous_quantity is None):
            raise ValueError("previous_line_total y previous_quantity van juntos.")
        if not CURRENCY.match(self.currency_code):
            raise ValueError("currency_code debe ser un código ISO 4217 en mayúsculas.")
        return self


class ApplicationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    price_list_id: UUID
    status: str


class PriceUpdateRequestAccepted(BaseModel):
    request_id: UUID
    applications: list[ApplicationSummary]


ResolutionReason = Annotated[str, BeforeValidator(_strip), Field(min_length=10, max_length=500)]


class ApplicationResolution(StrictModel):
    """A4: resolución administrativa de una aplicación `PENDING` o `FAILED` (FR-021-27)."""

    version: Version
    reason: ResolutionReason


class AutomaticPriceApplicationResponse(BaseModel):
    """A2 y A3 (`contracts/commercial-relationship.md` §4)."""

    id: UUID
    company_id: UUID
    request_id: UUID
    purchase_id: UUID
    purchase_detail_id: UUID
    price_list_id: UUID
    company_product_id: UUID
    company_product_presentation_id: UUID
    sequence: int
    received_at: AwareDatetime
    received_by_user_id: UUID
    policy_id: UUID | None
    markup_percentage: str | None
    current_unit_cost: str | None
    previous_unit_cost: str | None
    reference_cost: str | None
    previous_price: str | None
    new_price: str | None
    previous_price_item_id: UUID | None
    new_price_item_id: UUID | None
    cancelled_future_item_ids: list[UUID]
    status: str
    attempts: int
    next_attempt_at: AwareDatetime | None
    last_error_code: str | None
    first_attempt_at: AwareDatetime | None
    completed_at: AwareDatetime | None
    resolved_by: str | None
    resolution_reason: str | None
    version: int
    created_at: AwareDatetime
    updated_at: AwareDatetime
