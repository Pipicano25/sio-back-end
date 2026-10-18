"""Esquemas de la evolución de existencias (spec 023, INV-R1). Solo cantidades en unidad base: sin costos."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

from inventory_service.api.schemas.queries import PageQuery

MAX_SPAN = timedelta(days=366, hours=1)  # 366 días de la zona de la sucursal (con margen por cambios de hora)


class StockEvolutionQuery(PageQuery):
    from_: Annotated[AwareDatetime, Field(alias="from")]
    to: AwareDatetime
    company_product_id: Annotated[list[UUID], Field(max_length=100)] = []

    @model_validator(mode="after")
    def _range(self) -> "StockEvolutionQuery":
        if self.to <= self.from_:
            raise PydanticCustomError("INVALID_DATE_RANGE", "`to` debe ser posterior a `from`.")
        if self.to - self.from_ > MAX_SPAN:
            raise PydanticCustomError("PERIOD_TOO_LONG", "El período no puede superar 366 días.")
        return self


class ConsolidatedStockEvolutionQuery(StockEvolutionQuery):
    branch_id: Annotated[list[UUID], Field(min_length=1, max_length=100)]


def _q(value) -> str:
    return format(value, "f")


class StockEvolutionItem(BaseModel):
    company_product_id: UUID
    opening_quantity: str
    entries: str
    outputs: str
    entry_reversals: str
    output_reversals: str
    positive_adjustments: str
    negative_adjustments: str
    closing_quantity: str
    movement_count: int
    branch_count: int | None = None

    @classmethod
    def of(cls, row) -> "StockEvolutionItem":
        return cls(
            company_product_id=row.company_product_id,
            **{name: _q(getattr(row, name)) for name in (
                "opening_quantity", "entries", "outputs", "entry_reversals", "output_reversals",
                "positive_adjustments", "negative_adjustments", "closing_quantity")},
            movement_count=row.movement_count,
        )

    @classmethod
    def consolidated(cls, row) -> "StockEvolutionItem":
        item = cls.of(row)
        item.branch_count = row.branch_count
        return item


class StockEvolutionPage(BaseModel):
    company_id: UUID
    branch_id: UUID
    from_: Annotated[AwareDatetime, Field(serialization_alias="from")]
    to: AwareDatetime
    items: list[StockEvolutionItem]
    page: int
    page_size: int
    total_records: int
    total_pages: int


class ConsolidatedStockEvolutionPage(BaseModel):
    company_id: UUID
    branch_ids: list[UUID]
    from_: Annotated[AwareDatetime, Field(serialization_alias="from")]
    to: AwareDatetime
    items: list[StockEvolutionItem]
    page: int
    page_size: int
    total_records: int
    total_pages: int
