"""Schemas HTTP de métodos globales de pago."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from payment_reference_service.api.schemas.partial import PartialUpdate
from payment_reference_service.domain.global_payment_methods import (
    PaymentMethodStatus,
    PaymentMethodType,
)


class GlobalPaymentMethodCreate(BaseModel):
    """Payload para crear un método global de pago."""

    code: str = Field(max_length=40)
    name: str = Field(max_length=120)
    method_type: PaymentMethodType
    requires_reference: bool = False
    status: PaymentMethodStatus


class GlobalPaymentMethodUpdate(PartialUpdate):
    """`PUT` parcial (D28): solo los campos que cambian."""

    not_nullable = frozenset({"code", "name", "method_type", "requires_reference", "status"})

    code: str | None = Field(default=None, max_length=40)
    name: str | None = Field(default=None, max_length=120)
    method_type: PaymentMethodType | None = None
    requires_reference: bool | None = None
    status: PaymentMethodStatus | None = None


class GlobalPaymentMethodResponse(BaseModel):
    """Respuesta HTTP de un método global de pago."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    method_type: PaymentMethodType
    requires_reference: bool
    status: PaymentMethodStatus
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
