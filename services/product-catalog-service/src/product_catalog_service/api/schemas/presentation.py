"""Esquemas de presentaciones e identificadores (`contracts/rest-api.md` §6.4–§6.5)."""

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import Field

from product_catalog_service.api.schemas.base import RequestModel, UpdateModel
from product_catalog_service.api.schemas.product import FIRST_USE_FIELDS

IdentifierType = Literal["GTIN", "EAN", "UPC", "BARCODE", "OTHER", "IUM"]


class PresentationCreate(RequestModel):
    code: str = Field(max_length=120)
    name: str = Field(max_length=320)
    packaging_type_id: UUID | None = None
    base_quantity: Decimal = Decimal("1")
    content_quantity: Decimal | None = None
    content_unit_id: UUID | None = None
    display_order: int = Field(default=0, ge=0, le=32767)
    is_base: bool = False


class PresentationUpdate(UpdateModel):
    immutable_fields = frozenset({"code", "global_product_id", "status"}) | FIRST_USE_FIELDS

    name: str = Field(max_length=320)
    display_order: int = Field(ge=0, le=32767)
    packaging_type_id: UUID | None = None
    base_quantity: Decimal
    content_quantity: Decimal | None = None
    content_unit_id: UUID | None = None
    is_base: bool = False


class IdentifierCreate(RequestModel):
    identifier_type: IdentifierType
    value: str = Field(max_length=200)
    global_product_presentation_id: UUID | None = None
    is_primary: bool = False
