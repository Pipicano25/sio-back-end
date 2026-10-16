"""Esquemas de consultas por lotes, búsqueda por código y primer uso (US4)."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from product_catalog_service.api.schemas.base import RequestModel
from product_catalog_service.api.schemas.dependents import IdentifierResponse, PresentationResponse
from product_catalog_service.api.schemas.product import ProductResponse


class BatchLookupRequest(RequestModel):
    ids: list[UUID] = Field(description="Entre 1 y 100 identificadores; los repetidos se ignoran.")


class ProductLookupItem(BaseModel):
    id: UUID
    found: bool
    status: str | None = None
    is_complete: bool | None = None
    eligible_for_adoption: bool | None = None
    first_used_at: datetime | None = None


class PresentationLookupItem(BaseModel):
    id: UUID
    found: bool
    global_product_id: UUID | None = None
    # Campos aditivos (spec 021, H-2): Purchase copia código y nombre en la línea sin consultar una por una.
    code: str | None = None
    name: str | None = None
    status: str | None = None
    eligible_for_adoption: bool | None = None
    base_quantity: Decimal | None = None
    first_used_at: datetime | None = None


class UnitLookupItem(BaseModel):
    id: UUID
    found: bool
    status: str | None = None
    measurement_type: str | None = None
    allows_decimals: bool | None = None


class ProductLookupResponse(BaseModel):
    items: list[ProductLookupItem]


class PresentationLookupResponse(BaseModel):
    items: list[PresentationLookupItem]


class UnitLookupResponse(BaseModel):
    items: list[UnitLookupItem]


class FirstUseRequest(RequestModel):
    global_product_presentation_id: UUID | None = None


class FirstUseResponse(BaseModel):
    global_product_id: UUID
    product_first_used_at: datetime
    product_first_use_source: str
    global_product_presentation_id: UUID | None
    presentation_first_used_at: datetime | None
    presentation_first_use_source: str | None


class IdentifierLookupResponse(BaseModel):
    """Resultado de `GET /products/by-identifier/{value}` (FR-058)."""

    product: ProductResponse
    presentation: PresentationResponse | None
    identifier: IdentifierResponse
    is_current: bool
