"""Schemas HTTP de condiciones globales de pago."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from payment_reference_service.domain.global_payment_condition_types import (
    PaymentConditionStatus,
)


class GlobalPaymentConditionTypeCreate(BaseModel):
    """Payload para crear una condición global de pago."""

    code: str = Field(max_length=30)
    name: str = Field(max_length=100)
    description: str | None = None
    status: PaymentConditionStatus


class GlobalPaymentConditionTypeUpdate(BaseModel):
    """Payload para actualización completa mediante PUT."""

    code: str = Field(max_length=30)
    name: str = Field(max_length=100)
    description: str | None = None
    status: PaymentConditionStatus


class GlobalPaymentConditionTypeResponse(BaseModel):
    """Respuesta HTTP de una condición global de pago."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None
    status: PaymentConditionStatus
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime