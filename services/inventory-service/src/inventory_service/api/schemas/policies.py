"""Esquemas de políticas de inventario (`contracts/rest-api.md` rutas 21–28; 013).

`is_active` de la política de la empresa es solo de lectura: los cuerpos no lo aceptan
(`422 UNKNOWN_FIELD`) y no existe ruta de desactivación (C-07).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from inventory_service.domain.quantities import QuantityError, format_decimal, optional_decimal, parse_decimal

FIFO = "FIFO"


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return parse_decimal(value)
    except QuantityError as error:
        raise PydanticCustomError(error.code, error.message) from None


Level = Annotated[Decimal | None, BeforeValidator(_decimal)]


class _CompanyPolicyFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inventory_system: Literal["PERPETUAL", "PERIODIC"]
    valuation_method: str = FIFO
    replenishment_strategy: Literal["STANDARD", "JIT"]

    @field_validator("valuation_method")
    @classmethod
    def _fifo_only(cls, value: str) -> str:
        if value != FIFO:
            raise PydanticCustomError(
                "VALUATION_METHOD_NOT_SUPPORTED", "Esta fase solo admite la valoración FIFO (DS-11)."
            )
        return value


class CompanyPolicyIn(_CompanyPolicyFields):
    pass


class CompanyPolicyUpdateIn(_CompanyPolicyFields):
    version: int


class CompanyPolicyResponse(BaseModel):
    id: UUID | None
    company_id: UUID
    inventory_system: str
    valuation_method: str
    replenishment_strategy: str
    is_active: bool
    version: int | None
    registered: bool
    """`false`: la empresa no registró su política y se informa la política por defecto (DS-01)."""
    created_at: datetime | None
    created_by: str | None
    updated_at: datetime | None
    updated_by: str | None

    @classmethod
    def of(cls, company_id: UUID, row: Any | None) -> CompanyPolicyResponse:
        if row is None:
            return cls(
                id=None,
                company_id=company_id,
                inventory_system="PERPETUAL",
                valuation_method=FIFO,
                replenishment_strategy="STANDARD",
                is_active=True,
                version=None,
                registered=False,
                created_at=None,
                created_by=None,
                updated_at=None,
                updated_by=None,
            )
        return cls(
            id=row.id,
            company_id=row.company_id,
            inventory_system=row.inventory_system,
            valuation_method=row.valuation_method,
            replenishment_strategy=row.replenishment_strategy,
            is_active=row.is_active,
            version=row.version,
            registered=True,
            created_at=row.created_at,
            created_by=row.created_by,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )


class _ProductPolicyFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum_stock: Level = Decimal(0)
    target_stock: Level = None
    service_level: Level = None
    safety_stock_method: Literal["BASIC", "STATISTICAL"]
    calculation_window_days: int = 90
    replenishment_mode: Literal["MANUAL", "AUTO_DRAFT"]
    auto_purchase_enabled: bool = False


class ProductPolicyIn(_ProductPolicyFields):
    branch_id: UUID
    company_product_id: UUID


class ProductPolicyUpdateIn(_ProductPolicyFields):
    version: int


class VersionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int


class ProductPolicyResponse(BaseModel):
    id: UUID
    company_id: UUID
    branch_id: UUID
    company_product_id: UUID
    minimum_stock: str
    target_stock: str | None
    service_level: str | None
    safety_stock_method: str
    calculation_window_days: int
    replenishment_mode: str
    auto_purchase_enabled: bool
    is_active: bool
    version: int
    created_at: datetime
    created_by: str
    updated_at: datetime
    updated_by: str

    @classmethod
    def of(cls, row: Any) -> ProductPolicyResponse:
        return cls(
            id=row.id,
            company_id=row.company_id,
            branch_id=row.branch_id,
            company_product_id=row.company_product_id,
            minimum_stock=format_decimal(row.minimum_stock),
            target_stock=optional_decimal(row.target_stock),
            service_level=optional_decimal(row.service_level),
            safety_stock_method=row.safety_stock_method,
            calculation_window_days=row.calculation_window_days,
            replenishment_mode=row.replenishment_mode,
            auto_purchase_enabled=row.auto_purchase_enabled,
            is_active=row.is_active,
            version=row.version,
            created_at=row.created_at,
            created_by=row.created_by,
            updated_at=row.updated_at,
            updated_by=row.updated_by,
        )


class ProductPolicyPage(BaseModel):
    items: list[ProductPolicyResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int
