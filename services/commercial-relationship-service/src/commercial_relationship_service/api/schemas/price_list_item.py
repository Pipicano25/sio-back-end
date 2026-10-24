"""Esquemas de precios de lista y precio aplicable (`contracts/rest-api.md` §5 y §6 de la 010).

`unit_price` se presenta con los decimales de la moneda **de la lista**
(DS-10, R-11) y `currency_code` es el de la lista (solo lectura).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, field_serializer

from commercial_relationship_service.api.schemas.common import (
    AuditedResponse,
    StrictModel,
    UnitPrice,
    UpdateModel,
    Version,
)
from commercial_relationship_service.domain.currency import CURRENCY_DECIMALS, format_amount


class PriceListItemCreate(StrictModel):
    """Registro (FR-050); `valid_from` por defecto es el instante del servidor.

    Spec 019: todo precio es de una presentación (`company_product_presentation_id` obligatorio).
    """

    price_list_id: UUID
    company_product_id: UUID
    unit_price: UnitPrice
    company_product_presentation_id: UUID
    valid_from: AwareDatetime | None = None
    valid_to: AwareDatetime | None = None


class PriceListItemUpdate(UpdateModel):
    """`PUT` (FR-054): en vigencia solo cambia `valid_to`."""

    immutable_fields = frozenset(
        {"price_list_id", "company_product_id", "company_product_presentation_id", "company_id", "status"}
    )

    unit_price: UnitPrice
    valid_from: AwareDatetime
    valid_to: AwareDatetime | None = None


class PriceChangeRequest(StrictModel):
    """`change-price` (FR-054a): `effective_from` por defecto es el instante del servidor."""

    unit_price: UnitPrice
    effective_from: AwareDatetime | None = None
    version: Version


def _price(value: Decimal | None, currency_code: str | None) -> str | None:
    if value is None:
        return None
    return format_amount(value, CURRENCY_DECIMALS.get(currency_code or "", 2))


class PriceListItemResponse(AuditedResponse):
    price_list_id: UUID
    company_product_id: UUID
    company_product_presentation_id: UUID | None
    unit_price: Decimal
    currency_code: str
    valid_from: AwareDatetime
    valid_to: AwareDatetime | None
    # Spec 021 (FR-021-24): origen y cierre automáticos; sin costos ni porcentajes (FR-021-32a).
    origin: str | None = None
    closure_reason: str | None = None
    automatic_application_id: UUID | None = None

    @field_serializer("unit_price")
    def _unit_price(self, value: Decimal) -> str:
        return _price(value, self.currency_code)


class PriceChangeResponse(BaseModel):
    item: PriceListItemResponse
    previous: PriceListItemResponse


class ApplicablePriceLine(StrictModel):
    line_id: str | None = Field(default=None, max_length=64)
    company_product_id: UUID
    company_product_presentation_id: UUID  # spec 019: el precio siempre es de una presentación
    price_list_id: UUID | None = None


class ApplicablePriceRequest(StrictModel):
    """De 1 a 100 líneas (más → `422 BATCH_LIMIT_EXCEEDED`)."""

    at: AwareDatetime | None = None
    lines: list[ApplicablePriceLine] = Field(min_length=1)
    fallback_to_highest_price: bool = Field(
        default=False,
        description="Sin lista indicada y sin precio en la predeterminada: el precio más alto de las demás listas "
        "activas y vigentes en la moneda del producto. Lo usa Product Inventory Query.",
    )


class ApplicablePriceItem(BaseModel):
    line_id: str | None
    found: bool
    resolution: str
    basis: str | None = None
    unit_price: Decimal | None = None
    currency_code: str | None = None
    price_list_id: UUID | None = None
    price_list_item_id: UUID | None = None
    company_product_status: str | None = None
    presentation_status: str | None = None

    @field_serializer("unit_price")
    def _unit_price(self, value: Decimal | None) -> str | None:
        return _price(value, self.currency_code)


class ApplicablePriceResponse(BaseModel):
    at: AwareDatetime
    items: list[ApplicablePriceItem]
