"""Esquemas de las políticas de precios de lista (spec 021, `contracts/commercial-relationship.md` §1).

El porcentaje se recibe como número o texto decimal y lo valida el dominio (`MARKUP_PERCENTAGE_OUT_OF_RANGE`); se
presenta con 4 decimales. Las respuestas no incluyen costos (FR-021-32a).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, BeforeValidator, ConfigDict, Field

from commercial_relationship_service.api.schemas.common import (
    AuditedResponse,
    CurrencyCode,
    PercentageOut,
    StrictModel,
    Version,
    _strip,
)


def _reject_bool(value: Any) -> Any:
    if isinstance(value, bool):
        return "invalid"  # el dominio lo rechaza con MARKUP_PERCENTAGE_OUT_OF_RANGE
    return value


PolicyName = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=120)]
MarkupIn = Annotated[str | int | float | Decimal, BeforeValidator(_reject_bool)]
PresentationIds = Annotated[list[UUID], Field(max_length=1000)]
Reason = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=500)]


class PricingPolicyCreate(StrictModel):
    """Creación (FR-021-01): nombre, porcentaje inicial y presentaciones (de 0 a 100)."""

    name: PolicyName
    markup_percentage: MarkupIn
    company_product_presentation_ids: PresentationIds = []


class PricingPolicyRename(StrictModel):
    version: Version
    name: PolicyName


class PercentageChange(StrictModel):
    version: Version
    markup_percentage: MarkupIn


class PresentationsChange(StrictModel):
    version: Version
    company_product_presentation_ids: PresentationIds


class PolicyDeactivation(StrictModel):
    version: Version
    reason: Reason


class PricingPolicyResponse(AuditedResponse):
    price_list_id: UUID
    name: str
    markup_percentage: PercentageOut | None
    presentation_count: int
    deactivated_at: AwareDatetime | None
    deactivation_reason: str | None


class PolicyTermResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    markup_percentage: PercentageOut
    valid_from: AwareDatetime
    valid_to: AwareDatetime | None
    created_by: str
    closed_by: str | None


class PolicyPresentationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_product_presentation_id: UUID
    valid_from: AwareDatetime
    valid_to: AwareDatetime | None
    created_by: str
    closed_by: str | None


class CoverageRequest(StrictModel):
    """Cobertura de políticas (FR-021-35): moneda de la compra y de 1 a 100 presentaciones (sin repetidos)."""

    currency_code: CurrencyCode
    company_product_presentation_ids: list[UUID] = Field(min_length=1)


class CoverageItemResponse(BaseModel):
    """Solo cobertura: sin porcentajes, costos ni políticas (FR-021-32a)."""

    company_product_presentation_id: UUID
    found: bool
    covered: bool
    price_list_ids: list[UUID]


class CoverageResponse(BaseModel):
    items: list[CoverageItemResponse]
