"""Esquemas de listas de precios (`contracts/rest-api.md` §4 de la 010)."""

from __future__ import annotations

from pydantic import AwareDatetime

from commercial_relationship_service.api.schemas.common import (
    AuditedResponse,
    CurrencyCode,
    Description,
    PriceListCode,
    PriceListName,
    StrictModel,
    UpdateModel,
)


class PriceListCreate(StrictModel):
    """Creación (FR-040)."""

    code: PriceListCode
    name: PriceListName
    currency_code: CurrencyCode
    description: Description = None
    valid_from: AwareDatetime | None = None
    valid_to: AwareDatetime | None = None
    is_default: bool = False


class PriceListUpdate(UpdateModel):
    """`PUT` (FR-044): la moneda es inmutable (DS-09)."""

    immutable_fields = frozenset({"currency_code", "company_id", "status"})

    code: PriceListCode
    name: PriceListName
    description: Description = None
    valid_from: AwareDatetime | None = None
    valid_to: AwareDatetime | None = None
    is_default: bool


class PriceListResponse(AuditedResponse):
    code: str
    name: str
    description: str | None
    currency_code: str
    is_default: bool
    valid_from: AwareDatetime | None
    valid_to: AwareDatetime | None
