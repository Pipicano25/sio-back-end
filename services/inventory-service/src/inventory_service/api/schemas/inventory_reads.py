"""Esquemas de las lecturas de la spec 022: INV-1, INV-2 e INV-3 (`contracts/inventory.md` de la spec 022).

Ninguna respuesta tiene costos unitarios, costo promedio ni FIFO; INV-3 entrega el valor total solo si se
pide y está autorizado.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from inventory_service.api.schemas.queries import MAX_LOOKUP

MAX_BRANCHES = 100
SET_LIMIT_MAX = 100
MinimumState = Literal["BELOW_MINIMUM", "AT_MINIMUM", "ABOVE_MINIMUM", "WITH_POLICY"]


def _unique(value: list[UUID], *, field: str, limit: int) -> list[UUID]:
    unique = list(dict.fromkeys(value))
    if not 1 <= len(unique) <= limit:
        raise PydanticCustomError("INVALID_FORMAT", f"`{field}` debe tener entre 1 y {limit} elementos.")
    return unique


# ----------------------------------------------------------------------------- INV-1


class PolicyLookupIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_product_ids: list[UUID]

    @field_validator("company_product_ids")
    @classmethod
    def _size(cls, value: list[UUID]) -> list[UUID]:
        return _unique(value, field="company_product_ids", limit=MAX_LOOKUP)


class PolicySummary(BaseModel):
    id: UUID
    minimum_stock: str
    status: Literal["ACTIVE"]


class PolicyLookupItem(BaseModel):
    company_product_id: UUID
    policy: PolicySummary | None


class PolicyLookupResponse(BaseModel):
    items: list[PolicyLookupItem]


# ----------------------------------------------------------------------------- INV-2


class SetPosition(BaseModel):
    """Posición *keyset* que devuelve INV-2; se reenvía sin modificarla en `after`."""

    model_config = ConfigDict(extra="forbid")

    k: list[str] = Field(max_length=1)
    id: UUID
    branch_id: UUID | None = None


class ProductSetsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_ids: list[UUID]
    stock_state: Literal["IN_STOCK"] | None = None
    minimum_state: MinimumState | None = None
    unit: Literal["PRODUCTS", "PAIRS"] = "PRODUCTS"
    after: SetPosition | None = None
    limit: int = Field(ge=1, le=SET_LIMIT_MAX)

    @field_validator("branch_ids")
    @classmethod
    def _branches(cls, value: list[UUID]) -> list[UUID]:
        return _unique(value, field="branch_ids", limit=MAX_BRANCHES)

    @model_validator(mode="after")
    def _criteria(self) -> ProductSetsIn:
        if self.stock_state is None and self.minimum_state is None:
            raise PydanticCustomError("INVALID_FORMAT", "Indique `stock_state`, `minimum_state` o ambos.")
        if self.unit == "PAIRS":
            if self.minimum_state != "BELOW_MINIMUM" or self.stock_state is not None:
                raise PydanticCustomError(
                    "INVALID_FORMAT", "`unit = PAIRS` solo se usa con `minimum_state = BELOW_MINIMUM` y sin `stock_state`."
                )
            if self.after is not None:
                if len(self.after.k) != 1 or self.after.branch_id is None:
                    raise PydanticCustomError("INVALID_FORMAT", "`after` no corresponde a una posición de pares.")
                try:
                    Decimal(self.after.k[0])
                except InvalidOperation as exc:
                    raise PydanticCustomError("INVALID_FORMAT", "`after` no corresponde a una posición de pares.") from exc
        elif self.after is not None and (self.after.k or self.after.branch_id is not None):
            raise PydanticCustomError("INVALID_FORMAT", "`after` no corresponde a una posición de productos.")
        return self


class ProductSetItem(BaseModel):
    company_product_id: UUID
    position: SetPosition


class PairSetItem(BaseModel):
    company_product_id: UUID
    branch_id: UUID
    base_quantity: str
    minimum_stock: str
    shortfall: str
    position: SetPosition


class ProductSetsResponse(BaseModel):
    """Sin `total` ni conteo: `has_more` indica si hay más (spec 022, A-20)."""

    items: list[ProductSetItem] | list[PairSetItem]
    has_more: bool


# ----------------------------------------------------------------------------- INV-3


class InventorySummaryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_ids: list[UUID]
    include_valuation: bool = False

    @field_validator("branch_ids")
    @classmethod
    def _branches(cls, value: list[UUID]) -> list[UUID]:
        return _unique(value, field="branch_ids", limit=MAX_BRANCHES)


class SummaryCounts(BaseModel):
    products_with_positive_balance: int
    products_with_zero_balance: int
    products_with_policy: int
    products_below_minimum: int
    inventory_value: str | None = None


class BranchSummary(SummaryCounts):
    branch_id: UUID


class InventorySummaryResponse(BaseModel):
    branches: list[BranchSummary]
    consolidated: SummaryCounts
