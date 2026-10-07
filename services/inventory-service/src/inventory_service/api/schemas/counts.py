"""Esquemas de conteos físicos (`contracts/rest-api.md` rutas 14–20; 013)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from pydantic_core import PydanticCustomError

from inventory_service.api.schemas.adjustments import InventoryAdjustmentResponse, RequiredReason
from inventory_service.api.schemas.operations import UnitCost
from inventory_service.domain.quantities import QuantityError, format_decimal, optional_decimal, parse_unit_cost

OBSERVATIONS_MAX_LENGTH = 2000


def _observations(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value.strip()) > OBSERVATIONS_MAX_LENGTH:
        raise PydanticCustomError("INVALID_FORMAT", f"Las observaciones admiten a lo sumo {OBSERVATIONS_MAX_LENGTH} caracteres.")
    return value.strip() or None


def _counted(value: Any):
    """Cantidad contada: ≥ 0 (puede ser 0), a lo sumo 4 decimales."""
    try:
        return parse_unit_cost(value)
    except QuantityError as error:
        code = "QUANTITY_NOT_POSITIVE" if error.code == "UNIT_COST_NEGATIVE" else error.code
        raise PydanticCustomError(code, "La cantidad contada debe ser un número ≥ 0 con a lo sumo 4 decimales.") from None


class CountCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch_id: UUID
    observations: Annotated[str | None, BeforeValidator(_observations)] = None


class CountTransitionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int


class CountDetailIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counted_quantity: Annotated[Any, BeforeValidator(_counted)]
    unit_cost: UnitCost = None


class CountCompleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    completion_key: UUID
    version: int


class CountCancelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: RequiredReason = Field(default=None, validate_default=True)
    version: int


class InventoryCountDetailResponse(BaseModel):
    id: UUID
    inventory_count_id: UUID
    company_product_id: UUID
    system_quantity_snapshot: str
    counted_quantity: str
    difference_quantity: str
    unit_cost: str | None
    inventory_adjustment_id: UUID | None
    counted_by_user_id: UUID
    counted_at: datetime

    @classmethod
    def of(cls, row: Any) -> InventoryCountDetailResponse:
        return cls(
            id=row.id,
            inventory_count_id=row.inventory_count_id,
            company_product_id=row.company_product_id,
            system_quantity_snapshot=format_decimal(row.system_quantity_snapshot),
            counted_quantity=format_decimal(row.counted_quantity),
            difference_quantity=format_decimal(row.difference_quantity),
            unit_cost=optional_decimal(row.unit_cost),
            inventory_adjustment_id=row.inventory_adjustment_id,
            counted_by_user_id=row.counted_by_user_id,
            counted_at=row.counted_at,
        )


class InventoryCountResponse(BaseModel):
    id: UUID
    company_id: UUID
    branch_id: UUID
    status: str
    started_by_user_id: UUID
    started_at: datetime | None
    completed_by_user_id: UUID | None
    completed_at: datetime | None
    cancelled_by_user_id: UUID | None
    cancelled_at: datetime | None
    cancel_reason: str | None
    operation_id: UUID | None
    observations: str | None
    version: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str
    details: list[InventoryCountDetailResponse] | None = None
    adjustments: list[InventoryAdjustmentResponse] | None = None

    @classmethod
    def of(cls, row: Any, details: Any = None, adjustments: Any = None) -> InventoryCountResponse:
        extra: dict[str, Any] = {}
        if details is not None:
            extra["details"] = [InventoryCountDetailResponse.of(item) for item in details]
        if adjustments is not None:
            extra["adjustments"] = [InventoryAdjustmentResponse.of(row_, movement) for row_, movement in adjustments]
        return cls(
            id=row.id,
            company_id=row.company_id,
            branch_id=row.branch_id,
            status=row.status,
            started_by_user_id=row.started_by_user_id,
            started_at=row.started_at,
            completed_by_user_id=row.completed_by_user_id,
            completed_at=row.completed_at,
            cancelled_by_user_id=row.cancelled_by_user_id,
            cancelled_at=row.cancelled_at,
            cancel_reason=row.cancel_reason,
            operation_id=row.operation_id,
            observations=row.observations,
            version=row.version,
            created_at=row.created_at,
            created_by=row.created_by,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
            **extra,
        )


class CountPage(BaseModel):
    items: list[InventoryCountResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int
