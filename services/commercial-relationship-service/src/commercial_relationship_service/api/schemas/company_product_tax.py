"""Esquemas de la tasa de impuesto de compra del producto (spec 021, `contracts/commercial-relationship.md` §2).

La tasa se recibe como número o texto decimal y la valida el dominio (`TAX_PERCENTAGE_OUT_OF_RANGE`,
`PURCHASE_TAX_REQUIRED`); se presenta con 4 decimales.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, Field, field_validator

from commercial_relationship_service.api.schemas.common import StrictModel, Version
from commercial_relationship_service.api.schemas.company_product import CompanyProductResponse


def _keep_bool(value: Any) -> Any:
    return "invalid" if isinstance(value, bool) else value  # el dominio lo rechaza


TaxIn = Annotated[str | int | float | Decimal | None, BeforeValidator(_keep_bool)]


class PurchaseTaxUpdate(StrictModel):
    version: Version
    purchase_tax_percentage: TaxIn


class PurchaseTaxItem(StrictModel):
    company_product_id: UUID
    version: Version
    purchase_tax_percentage: TaxIn


class PurchaseTaxBatch(StrictModel):
    items: list[PurchaseTaxItem] = Field(min_length=1)

    @field_validator("items")
    @classmethod
    def _distinct(cls, items: list[PurchaseTaxItem]) -> list[PurchaseTaxItem]:
        if len({item.company_product_id for item in items}) != len(items):
            raise ValueError("Cada producto aparece una sola vez en el lote.")
        return items


class PurchaseTaxBatchResponse(BaseModel):
    items: list[CompanyProductResponse]
