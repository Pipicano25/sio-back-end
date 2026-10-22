"""Esquemas de la spec 022: PC-1 (resumen por lotes) y PC-2 (productos por filtros)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from product_catalog_service.api.schemas.base import RequestModel

MATCH_LIMIT_MAX = 100


class SummaryReference(BaseModel):
    id: UUID
    code: str
    name: str


class SummaryCategory(SummaryReference):
    is_primary: bool


class SummaryIdentifier(BaseModel):
    type: str
    value: str
    is_primary: bool
    global_product_presentation_id: UUID | None


class ProductSummaryItem(BaseModel):
    """Producto global del lote; si no existe, solo `id` y `found = false`."""

    model_config = {"json_schema_extra": {"description": "Sin datos privados de empresas ni rutas internas."}}

    id: UUID
    found: bool
    canonical_name: str | None = None
    product_type: str | None = None
    status: str | None = None
    brand: SummaryReference | None = None
    base_unit: SummaryReference | None = None
    categories: list[SummaryCategory] | None = None
    identifiers: list[SummaryIdentifier] | None = None
    has_image: bool | None = None
    image_asset_id: UUID | None = None
    image_url: str | None = None


class ProductSummaryResponse(BaseModel):
    items: list[ProductSummaryItem]


class MatchPosition(RequestModel):
    """Posición *keyset*: nombre canónico normalizado (`k`) e `id`; se reenvía sin modificarla."""

    k: list[str] = Field(min_length=1, max_length=1)
    id: UUID


class ProductMatchRequest(RequestModel):
    """PC-2. Con `candidate_ids` es modo evaluador; sin ellos, modo conductor (`after` y `limit`)."""

    brand_ids: list[UUID] = Field(default_factory=list, max_length=100)
    category_ids: list[UUID] = Field(default_factory=list, max_length=100)
    include_descendants: bool = False
    identifier: str | None = Field(default=None, min_length=1, max_length=120)
    product_type: str | None = Field(default=None, max_length=20)
    status: Literal["ACTIVE", "INACTIVE", "ALL"] = "ACTIVE"
    has_image: bool | None = None
    candidate_ids: list[UUID] | None = Field(default=None, min_length=1)
    after: MatchPosition | None = None
    limit: int | None = Field(default=None, ge=1, le=MATCH_LIMIT_MAX)

    @model_validator(mode="after")
    def _mode(self) -> "ProductMatchRequest":
        if self.candidate_ids is not None:
            if self.after is not None or self.limit is not None:
                raise ValueError("En modo evaluador (`candidate_ids`) no se envían `after` ni `limit`.")
            if len(set(self.candidate_ids)) > MATCH_LIMIT_MAX:
                raise ValueError(f"Se admiten como máximo {MATCH_LIMIT_MAX} candidatos.")
        elif self.limit is None:
            raise ValueError("En modo conductor `limit` es obligatorio.")
        return self


class ProductMatchEvaluatorResponse(BaseModel):
    ids: list[UUID]


class ProductMatchItem(BaseModel):
    id: UUID
    position: MatchPosition


class ProductMatchConductorResponse(BaseModel):
    """Sin conteos: `has_more` indica si quedan productos (spec 022, A-20)."""

    items: list[ProductMatchItem]
    has_more: bool
