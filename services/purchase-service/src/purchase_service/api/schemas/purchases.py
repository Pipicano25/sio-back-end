"""Esquemas de compras, líneas, confirmación y anulación (`contracts/rest-api.md` rutas 1–12).

Entradas con `extra="forbid"` (campo desconocido → `422 UNKNOWN_FIELD`); totales y
snapshots nunca se aceptan en el cuerpo. Spec 020: presentación obligatoria en toda línea,
`payment_method_id` obligatorio en la cabecera y recepción física completa (`ReceiptIn`). Decimales como cadena en las respuestas:
cantidades y costos unitarios con 4 decimales, montos con 2, factor con 8.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

from purchase_service.application.purchase_service import HeaderData, LineData, PurchaseView
from purchase_service.application.snapshots import line_base_quantity, line_inventory_cost
from purchase_service.domain.status import CONFIRMED, MAX_LINES, RECEIPT_PENDING, RECEIPT_RECEIVED
from purchase_service.infrastructure.models import PurchaseDetail, PurchaseOperation

QUANTITY = Decimal("0.0001")
MONEY = Decimal("0.01")
FACTOR = Decimal("0.00000001")


def fmt(value: Decimal | None, quantum: Decimal) -> str | None:
    return None if value is None else format(Decimal(value).quantize(quantum), "f")


def _finite(value: Decimal) -> Decimal:
    if not value.is_finite():
        raise PydanticCustomError("INVALID_FORMAT", "El valor no es un número decimal válido.")
    return value


DecimalIn = Annotated[Decimal, Field(allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LineIn(StrictModel):
    company_product_id: UUID
    company_product_presentation_id: UUID
    supplier_product_id: UUID | None = None
    quantity: DecimalIn
    unit_cost: DecimalIn
    discount_amount: DecimalIn = Decimal("0")
    # Spec 021 (DS-03): `tax_amount` ya no se acepta (campo desconocido → `422`); lo calcula el servidor desde la tasa.
    # `tax_percentage` ajusta la tasa de la línea y exige `perm:purchase:purchase_line_taxes:override` (FR-021-11).
    tax_percentage: str | int | float | Decimal | None = None

    def to_data(self) -> LineData:
        return LineData(
            company_product_id=self.company_product_id,
            company_product_presentation_id=self.company_product_presentation_id,
            supplier_product_id=self.supplier_product_id,
            quantity=self.quantity,
            unit_cost=self.unit_cost,
            discount_amount=self.discount_amount,
            tax_percentage=self.tax_percentage,
        )


class HeaderIn(StrictModel):
    branch_id: UUID
    company_supplier_id: UUID
    operation_date: date
    supplier_payment_condition_id: UUID | None = None
    payment_method_id: UUID
    promised_delivery_at: AwareDatetime | None = None
    supplier_document_number: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    observations: Annotated[str, Field(max_length=2000)] | None = None

    def to_header(self) -> HeaderData:
        return HeaderData(
            branch_id=self.branch_id,
            company_supplier_id=self.company_supplier_id,
            operation_date=self.operation_date,
            supplier_payment_condition_id=self.supplier_payment_condition_id,
            promised_delivery_at=self.promised_delivery_at,
            supplier_document_number=self.supplier_document_number,
            observations=self.observations,
            payment_method_id=self.payment_method_id,
        )


class PurchaseCreateIn(HeaderIn):
    lines: list[LineIn] = Field(default_factory=list)

    @field_validator("lines", mode="before")
    @classmethod
    def _limit(cls, value):
        if isinstance(value, list) and len(value) > MAX_LINES:
            raise PydanticCustomError("LINES_LIMIT_EXCEEDED", f"Una compra admite a lo sumo {MAX_LINES} líneas.")
        return value


class PurchaseUpdateIn(HeaderIn):
    version: Annotated[int, Field(ge=1)]


class LineCreateIn(LineIn):
    version: Annotated[int, Field(ge=1)]


class VersionIn(StrictModel):
    version: Annotated[int, Field(ge=1)]


class ReceiptIn(StrictModel):
    """Recepción física completa (spec 020, FR-020-02): el usuario confirma que recibió **toda** la compra."""

    version: Annotated[int, Field(ge=1)]
    full_receipt_confirmed: bool


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


class PurchaseDetailResponse(BaseModel):
    id: UUID
    purchase_id: UUID
    line_number: int
    company_product_id: UUID
    company_product_presentation_id: UUID | None
    supplier_product_id: UUID | None
    supplier_lead_time_snapshot_hours: str | None
    product_code_snapshot: str
    product_name_snapshot: str
    presentation_code_snapshot: str | None
    presentation_name_snapshot: str | None
    base_quantity_factor_snapshot: str
    unit_code_snapshot: str
    quantity: str
    unit_cost: str
    discount_amount: str
    tax_amount: str
    tax_percentage: str | None
    tax_percentage_source: str | None
    warnings: list[str]
    subtotal: str
    total: str
    base_quantity: str
    inventory_unit_cost: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str

    @classmethod
    def of(cls, detail: PurchaseDetail, uncovered: frozenset = frozenset()) -> PurchaseDetailResponse:
        return cls(
            id=detail.id,
            purchase_id=detail.purchase_id,
            line_number=detail.line_number,
            company_product_id=detail.company_product_id,
            company_product_presentation_id=detail.company_product_presentation_id,
            supplier_product_id=detail.supplier_product_id,
            supplier_lead_time_snapshot_hours=fmt(detail.supplier_lead_time_snapshot_hours, MONEY),
            product_code_snapshot=detail.product_code_snapshot,
            product_name_snapshot=detail.product_name_snapshot,
            presentation_code_snapshot=detail.presentation_code_snapshot,
            presentation_name_snapshot=detail.presentation_name_snapshot,
            base_quantity_factor_snapshot=fmt(detail.base_quantity_factor_snapshot, FACTOR),
            unit_code_snapshot=detail.unit_code_snapshot,
            quantity=fmt(detail.quantity, QUANTITY),
            unit_cost=fmt(detail.unit_cost, QUANTITY),
            discount_amount=fmt(detail.discount_amount, MONEY),
            tax_amount=fmt(detail.tax_amount, MONEY),
            tax_percentage=fmt(detail.tax_percentage, QUANTITY),
            tax_percentage_source=detail.tax_percentage_source,
            warnings=(["PURCHASE_TAX_NOT_CONFIGURED"] if detail.tax_percentage is None else [])
            # spec 021 (FR-021-36): solo en las respuestas que crean, agregan o editan líneas
            + (["PRICING_POLICY_NOT_CONFIGURED"] if detail.company_product_presentation_id in uncovered else []),
            subtotal=fmt(detail.subtotal, MONEY),
            total=fmt(detail.total, MONEY),
            base_quantity=fmt(line_base_quantity(detail), QUANTITY),
            inventory_unit_cost=fmt(line_inventory_cost(detail), QUANTITY),
            created_at=detail.created_at,
            updated_at=detail.updated_at,
            created_by=detail.created_by,
            updated_by=detail.updated_by,
        )


def receipt_status(status: str, received_at: datetime | None) -> str | None:
    """Spec 020 (FR-020-05): `RECEIVED` si se recibió (aunque luego se anule); `PENDING` si está
    confirmada sin recibir; nulo en borrador o anulada sin recibir."""
    if received_at is not None:
        return RECEIPT_RECEIVED
    return RECEIPT_PENDING if status == CONFIRMED else None


class PurchaseResponse(BaseModel):
    id: UUID
    company_id: UUID
    branch_id: UUID
    company_supplier_id: UUID
    supplier_payment_condition_id: UUID | None
    payment_condition_code_snapshot: str
    payment_terms_days_snapshot: int
    due_date: date
    payment_method_id: UUID | None
    payment_method_code_snapshot: str | None
    payment_method_name_snapshot: str | None
    purchase_sequence_id: UUID | None
    number: str | None
    sequence_value: int | None
    status: str
    operation_date: date
    promised_delivery_at: datetime | None
    supplier_document_number: str | None
    supplier_name_snapshot: str
    supplier_identification_snapshot: str
    currency_code: str
    observations: str | None
    subtotal: str
    discount_total: str
    tax_total: str
    total: str
    inventory_operation_id: UUID | None
    receipt_status: str | None
    received_at: datetime | None
    received_by_user_id: UUID | None
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
    lines: list[PurchaseDetailResponse] | None = None

    @classmethod
    def of(cls, view: PurchaseView, *, with_lines: bool = True) -> PurchaseResponse:
        purchase = view.purchase
        return cls(
            id=purchase.id,
            company_id=purchase.company_id,
            branch_id=purchase.branch_id,
            company_supplier_id=purchase.company_supplier_id,
            supplier_payment_condition_id=purchase.supplier_payment_condition_id,
            payment_condition_code_snapshot=purchase.payment_condition_code_snapshot,
            payment_terms_days_snapshot=purchase.payment_terms_days_snapshot,
            due_date=purchase.due_date,
            payment_method_id=purchase.payment_method_id,
            payment_method_code_snapshot=purchase.payment_method_code_snapshot,
            payment_method_name_snapshot=purchase.payment_method_name_snapshot,
            purchase_sequence_id=purchase.purchase_sequence_id,
            number=purchase.number,
            sequence_value=purchase.sequence_value,
            status=purchase.status,
            operation_date=purchase.operation_date,
            promised_delivery_at=purchase.promised_delivery_at,
            supplier_document_number=purchase.supplier_document_number,
            supplier_name_snapshot=purchase.supplier_name_snapshot,
            supplier_identification_snapshot=purchase.supplier_identification_snapshot,
            currency_code=purchase.currency_code,
            observations=purchase.observations,
            subtotal=fmt(purchase.subtotal, MONEY),
            discount_total=fmt(purchase.discount_total, MONEY),
            tax_total=fmt(purchase.tax_total, MONEY),
            total=fmt(purchase.total, MONEY),
            inventory_operation_id=purchase.inventory_operation_id,
            receipt_status=receipt_status(purchase.status, purchase.received_at),
            received_at=purchase.received_at,
            received_by_user_id=purchase.received_by_user_id,
            created_by_user_id=purchase.created_by_user_id,
            cancelled_by_user_id=purchase.cancelled_by_user_id,
            cancelled_at=purchase.cancelled_at,
            cancellation_reason=purchase.cancellation_reason,
            pending_operation_id=view.pending_operation_id,
            version=purchase.version,
            created_at=purchase.created_at,
            updated_at=purchase.updated_at,
            created_by=purchase.created_by,
            updated_by=purchase.updated_by,
            lines=[PurchaseDetailResponse.of(line, view.uncovered) for line in view.lines] if with_lines else None,
        )


class PurchasePage(BaseModel):
    items: list[PurchaseResponse]
    page: int
    page_size: int
    total_records: int
    total_pages: int


class PurchaseQuery(StrictModel):
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 20
    status: Annotated[str, Field(pattern="^(DRAFT|CONFIRMED|CANCELLED)$")] | None = None
    branch_id: UUID | None = None
    company_supplier_id: UUID | None = None
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


class OperationResponse(BaseModel):
    """`purchase_operations` sin `idempotency_key` (no se expone)."""

    id: UUID
    purchase_id: UUID
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
    def of(cls, operation: PurchaseOperation) -> OperationResponse:
        return cls(
            id=operation.id,
            purchase_id=operation.purchase_id,
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
