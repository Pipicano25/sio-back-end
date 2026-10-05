"""Esquemas de condiciones de pago (`contracts/rest-api.md` §3 de la 010).

La respuesta no incluye `code` ni `name` del tipo de condición (Principio III,
FR-038). `credit_limit` se presenta con los decimales de su moneda (R-11).
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import AwareDatetime, field_serializer

from commercial_relationship_service.api.schemas.common import (
    AuditedResponse,
    CreditLimit,
    CurrencyCode,
    PaymentTermsDays,
    Percentage,
    PercentageOut,
    StrictModel,
    UpdateModel,
)
from commercial_relationship_service.domain.currency import CURRENCY_DECIMALS, format_amount


class SupplierPaymentConditionCreate(StrictModel):
    """Registro (FR-030); `valid_from` por defecto es el instante del servidor."""

    company_supplier_id: UUID
    payment_condition_type_id: UUID
    currency_code: CurrencyCode
    payment_terms_days: PaymentTermsDays = 0
    credit_limit: CreditLimit | None = None
    interest_rate_percentage: Percentage | None = None
    cash_discount_percentage: Percentage | None = None
    is_default: bool = False
    valid_from: AwareDatetime | None = None
    valid_to: AwareDatetime | None = None


class SupplierPaymentConditionUpdate(UpdateModel):
    """`PUT` (FR-036): el proveedor es inmutable."""

    immutable_fields = frozenset({"company_supplier_id", "company_id", "status"})

    payment_condition_type_id: UUID
    currency_code: CurrencyCode
    payment_terms_days: PaymentTermsDays
    credit_limit: CreditLimit | None = None
    interest_rate_percentage: Percentage | None = None
    cash_discount_percentage: Percentage | None = None
    is_default: bool
    valid_from: AwareDatetime
    valid_to: AwareDatetime | None = None


class SupplierPaymentConditionResponse(AuditedResponse):
    company_supplier_id: UUID
    payment_condition_type_id: UUID
    currency_code: str
    payment_terms_days: int
    credit_limit: Decimal | None
    interest_rate_percentage: PercentageOut | None
    cash_discount_percentage: PercentageOut | None
    is_default: bool
    valid_from: AwareDatetime
    valid_to: AwareDatetime | None

    @field_serializer("credit_limit")
    def _credit_limit(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return format_amount(value, CURRENCY_DECIMALS.get(self.currency_code, 2))
