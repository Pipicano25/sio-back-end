"""Esquemas de ventas, líneas, disponibilidad, confirmación y anulación (`contracts/rest-api.md` rutas 1–13).

Entradas con `extra="forbid"` (campo desconocido → `422 UNKNOWN_FIELD`). Nunca se aceptan
precio (`UNIT_PRICE_NOT_ALLOWED`, DS-11), fecha de negocio (`OPERATION_DATE_NOT_ALLOWED`,
R-12) ni condición de pago (`PAYMENT_CONDITION_NOT_ALLOWED`, DP-01); tampoco totales,
snapshots, costos ni márgenes. Decimales como cadena en las respuestas: cantidades,
precios y costos unitarios con 4 decimales, montos con 2, factor con 8, porcentaje con 4.

Los campos de rentabilidad (`unit_cost_snapshot`, `cost_total`, `cost_known`,
`gross_margin_amount`, `gross_margin_percentage`, `has_unknown_cost`) solo se envían con
`perm:sales:sales:read-profitability` (FR-027a; `api/profitability.py`).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.json_schema import SkipJsonSchema
from pydantic_core import PydanticCustomError

from sales_service.application.availability import ProductAvailability
from sales_service.application.sale_service import HeaderData, LineData, SaleView
from sales_service.application.snapshots import line_base_quantity
from sales_service.domain.status import MAX_LINES
from sales_service.infrastructure.models import Sale, SaleDetail, SaleOperation

QUANTITY = Decimal("0.0001")
MONEY = Decimal("0.01")
FACTOR = Decimal("0.00000001")
PRICE_LIST_ITEM = "PRICE_LIST_ITEM"
COMPANY_PRODUCT_SALE_PRICE = "COMPANY_PRODUCT_SALE_PRICE"


def fmt(value: Decimal | None, quantum: Decimal) -> str | None:
    return None if value is None else format(Decimal(value).quantize(quantum), "f")


DecimalIn = Annotated[Decimal, Field(allow_inf_nan=False)]
NotAllowed = SkipJsonSchema[Any]


def _reject(code: str, message: str):
    def check(value):
        raise PydanticCustomError(code, message)

    return check


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LineIn(StrictModel):
    company_product_id: UUID
    # Spec 019: toda línea indica su presentación (la de factor 1 para vender la unidad base).
    company_product_presentation_id: UUID
    price_list_id: UUID | None = None
    quantity: DecimalIn
    discount_amount: DecimalIn = Decimal("0")
    tax_amount: DecimalIn = Decimal("0")
    unit_price: NotAllowed = None

    _no_price = field_validator("unit_price")(
        _reject("UNIT_PRICE_NOT_ALLOWED", "El precio lo resuelve el sistema; no se admite precio manual.")
    )

    def to_data(self) -> LineData:
        return LineData(
            company_product_id=self.company_product_id,
            company_product_presentation_id=self.company_product_presentation_id,
            price_list_id=self.price_list_id,
            quantity=self.quantity,
            discount_amount=self.discount_amount,
            tax_amount=self.tax_amount,
        )


_PAYMENT_NOT_ALLOWED = _reject(
    "PAYMENT_CONDITION_NOT_ALLOWED", "Las ventas del MVP son de contado: no se admite condición de pago."
)


class HeaderIn(StrictModel):
    branch_id: UUID
    company_customer_id: UUID
    observations: Annotated[str, Field(max_length=2000)] | None = None
    operation_date: NotAllowed = None
    due_date: NotAllowed = None
    customer_payment_condition_id: NotAllowed = None
    payment_condition_code_snapshot: NotAllowed = None
    payment_terms_days_snapshot: NotAllowed = None

    _no_date = field_validator("operation_date")(
        _reject("OPERATION_DATE_NOT_ALLOWED", "La fecha de negocio la fija el sistema al confirmar la venta.")
    )
    _no_payment = field_validator(
        "due_date", "customer_payment_condition_id", "payment_condition_code_snapshot", "payment_terms_days_snapshot"
    )(_PAYMENT_NOT_ALLOWED)

    def to_header(self) -> HeaderData:
        return HeaderData(
            branch_id=self.branch_id,
            company_customer_id=self.company_customer_id,
            observations=self.observations,
        )


class SaleCreateIn(HeaderIn):
    lines: list[LineIn] = Field(default_factory=list)

    @field_validator("lines", mode="before")
    @classmethod
    def _limit(cls, value):
        if isinstance(value, list) and len(value) > MAX_LINES:
            raise PydanticCustomError("LINES_LIMIT_EXCEEDED", f"Una venta admite a lo sumo {MAX_LINES} líneas.")
        return value


class SaleUpdateIn(HeaderIn):
    version: Annotated[int, Field(ge=1)]


class LineCreateIn(LineIn):
    version: Annotated[int, Field(ge=1)]


class VersionIn(StrictModel):
    version: Annotated[int, Field(ge=1)]


class CancelIn(StrictModel):
    version: Annotated[int, Field(ge=1)]
    reason: str

    @field_validator("reason")
    @classmethod
    def _reason(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise PydanticCustomError("REASON_REQUIRED", "El motivo de la anulación es obligatorio.")
        if len(value) > 1000:
            raise PydanticCustomError("INVALID_FORMAT", "El motivo admite a lo sumo 1000 caracteres.")
        return value


class SaleDetailResponse(BaseModel):
    id: UUID
    sale_id: UUID
    line_number: int
    company_product_id: UUID
    company_product_presentation_id: UUID | None
    price_list_id: UUID | None
    price_list_item_id: UUID | None
    price_list_requested: bool
    price_source: str
    product_code_snapshot: str
    product_name_snapshot: str
    presentation_code_snapshot: str | None
    presentation_name_snapshot: str | None
    base_quantity_factor_snapshot: str
    unit_code_snapshot: str
    quantity: str
    base_quantity: str
    unit_price: str
    discount_amount: str
    tax_amount: str
    subtotal: str
    total: str
    unit_cost_snapshot: str | None = Field(
        default=None, description="Costo FIFO por unidad base (Inventory). Solo con read-profitability."
    )
    cost_total: str | None = Field(default=None, description="Solo con read-profitability.")
    cost_known: bool | None = Field(default=None, description="Solo con read-profitability.")
    gross_margin_amount: str | None = Field(default=None, description="Solo con read-profitability.")
    gross_margin_percentage: str | None = Field(default=None, description="Solo con read-profitability.")
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    @classmethod
    def of(cls, detail: SaleDetail) -> SaleDetailResponse:
        return cls(
            id=detail.id,
            sale_id=detail.sale_id,
            line_number=detail.line_number,
            company_product_id=detail.company_product_id,
            company_product_presentation_id=detail.company_product_presentation_id,
            price_list_id=detail.price_list_id,
            price_list_item_id=detail.price_list_item_id,
            price_list_requested=detail.price_list_requested,
            price_source=PRICE_LIST_ITEM if detail.price_list_item_id is not None else COMPANY_PRODUCT_SALE_PRICE,
            product_code_snapshot=detail.product_code_snapshot,
            product_name_snapshot=detail.product_name_snapshot,
            presentation_code_snapshot=detail.presentation_code_snapshot,
            presentation_name_snapshot=detail.presentation_name_snapshot,
            base_quantity_factor_snapshot=fmt(detail.base_quantity_factor_snapshot, FACTOR),
            unit_code_snapshot=detail.unit_code_snapshot,
            quantity=fmt(detail.quantity, QUANTITY),
            base_quantity=fmt(line_base_quantity(detail), QUANTITY),
            unit_price=fmt(detail.unit_price, QUANTITY),
            discount_amount=fmt(detail.discount_amount, MONEY),
            tax_amount=fmt(detail.tax_amount, MONEY),
            subtotal=fmt(detail.subtotal, MONEY),
            total=fmt(detail.total, MONEY),
            unit_cost_snapshot=fmt(detail.unit_cost_snapshot, QUANTITY),
            cost_total=fmt(detail.cost_total, MONEY),
            cost_known=detail.cost_known,
            gross_margin_amount=fmt(detail.gross_margin_amount, MONEY),
            gross_margin_percentage=fmt(detail.gross_margin_percentage, QUANTITY),
            created_at=detail.created_at,
            updated_at=detail.updated_at,
            created_by=detail.created_by,
            updated_by=detail.updated_by,
        )


class SaleResponse(BaseModel):
    id: UUID
    company_id: UUID
    branch_id: UUID
    company_customer_id: UUID
    customer_payment_condition_id: UUID | None
    payment_condition_code_snapshot: str
    payment_terms_days_snapshot: int
    due_date: date
    sale_sequence_id: UUID | None
    number: str | None
    sequence_value: int | None
    status: str
    operation_date: date
    customer_name_snapshot: str
    customer_identification_snapshot: str
    currency_code: str
    observations: str | None
    subtotal: str
    discount_total: str
    tax_total: str
    total: str
    has_unknown_cost: bool | None = Field(default=None, description="Solo con read-profitability.")
    inventory_operation_id: UUID | None
    created_by_user_id: UUID
    cancelled_by_user_id: UUID | None
    cancelled_at: datetime | None
    cancellation_reason: str | None
    pending_operation_id: UUID | None
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str
    lines: list[SaleDetailResponse] | None = None

    @classmethod
    def of(cls, view: SaleView, *, with_lines: bool = True) -> SaleResponse:
        sale: Sale = view.sale
        return cls(
            id=sale.id,
            company_id=sale.company_id,
            branch_id=sale.branch_id,
            company_customer_id=sale.company_customer_id,
            customer_payment_condition_id=sale.customer_payment_condition_id,
            payment_condition_code_snapshot=sale.payment_condition_code_snapshot,
            payment_terms_days_snapshot=sale.payment_terms_days_snapshot,
            due_date=sale.due_date,
            sale_sequence_id=sale.sale_sequence_id,
            number=sale.number,
            sequence_value=sale.sequence_value,
            status=sale.status,
            operation_date=sale.operation_date,
            customer_name_snapshot=sale.customer_name_snapshot,
            customer_identification_snapshot=sale.customer_identification_snapshot,
            currency_code=sale.currency_code,
            observations=sale.observations,
            subtotal=fmt(sale.subtotal, MONEY),
            discount_total=fmt(sale.discount_total, MONEY),
            tax_total=fmt(sale.tax_total, MONEY),
            total=fmt(sale.total, MONEY),
            has_unknown_cost=sale.has_unknown_cost,
            inventory_operation_id=sale.inventory_operation_id,
            created_by_user_id=sale.created_by_user_id,
            cancelled_by_user_id=sale.cancelled_by_user_id,
            cancelled_at=sale.cancelled_at,
            cancellation_reason=sale.cancellation_reason,
            pending_operation_id=view.pending_operation_id,
            version=sale.version,
            created_at=sale.created_at,
            updated_at=sale.updated_at,
            created_by=sale.created_by,
            updated_by=sale.updated_by,
            lines=[SaleDetailResponse.of(line) for line in view.lines] if with_lines else None,
        )


class SalePage(BaseModel):
    items: list[SaleResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int


class SaleQuery(StrictModel):
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 20
    status: Annotated[str, Field(pattern="^(DRAFT|CONFIRMED|CANCELLED)$")] | None = None
    branch_id: UUID | None = None
    company_customer_id: UUID | None = None
    operation_date_from: date | None = None
    operation_date_to: date | None = None
    number: Annotated[str, Field(min_length=1, max_length=80)] | None = None

    @field_validator("operation_date_to")
    @classmethod
    def _range(cls, value, info):
        start = info.data.get("operation_date_from")
        if value is not None and start is not None and value < start:
            raise PydanticCustomError("INVALID_DATE_RANGE", "La fecha final no puede ser anterior a la inicial.")
        return value


def total_pages(total_records: int, page_size: int) -> int:
    return (total_records + page_size - 1) // page_size if total_records else 0


class ProductAvailabilityResponse(BaseModel):
    company_product_id: UUID
    line_numbers: list[int]
    required_base_quantity: str
    available_base_quantity: str
    is_available: bool


class AvailabilityResponse(BaseModel):
    sale_id: UUID
    branch_id: UUID
    all_available: bool
    products: list[ProductAvailabilityResponse]

    @classmethod
    def of(cls, sale: Sale, rows: list[ProductAvailability]) -> AvailabilityResponse:
        return cls(
            sale_id=sale.id,
            branch_id=sale.branch_id,
            all_available=all(row.is_available for row in rows),
            products=[
                ProductAvailabilityResponse(
                    company_product_id=row.company_product_id,
                    line_numbers=row.line_numbers,
                    required_base_quantity=fmt(row.required_base_quantity, QUANTITY),
                    available_base_quantity=fmt(row.available_base_quantity, QUANTITY),
                    is_available=row.is_available,
                )
                for row in rows
            ],
        )


class OperationResponse(BaseModel):
    """`sale_operations` sin `idempotency_key`, usuario operativo ni motivo (no se exponen)."""

    id: UUID
    sale_id: UUID
    operation_type: str
    status: str
    correlation_id: UUID
    error_code: str | None
    error_details: dict | None
    inventory_operation_id: UUID | None
    started_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    @classmethod
    def of(cls, operation: SaleOperation) -> OperationResponse:
        return cls(
            id=operation.id,
            sale_id=operation.sale_id,
            operation_type=operation.operation_type,
            status=operation.status,
            correlation_id=operation.correlation_id,
            error_code=operation.error_code,
            error_details=operation.error_details,
            inventory_operation_id=operation.inventory_operation_id,
            started_at=operation.started_at,
            updated_at=operation.updated_at,
            completed_at=operation.completed_at,
        )

