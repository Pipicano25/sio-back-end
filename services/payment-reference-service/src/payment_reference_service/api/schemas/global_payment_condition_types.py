"""Schemas HTTP de tipos globales de condición de pago.

Feature 008 (FR-016b): los cuerpos de alta, `PUT` y acciones rechazan cualquier
campo no definido (`extra="forbid"` → `422`); `status` no forma parte del alta ni
del `PUT`: solo cambia con `deactivate`/`reactivate`.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from payment_reference_service.api.schemas.partial import PartialUpdate
from payment_reference_service.domain.global_payment_condition_types import (
    PaymentConditionStatus,
)


class GlobalPaymentConditionTypeCreate(BaseModel):
    """Payload para crear un tipo global de condición de pago (siempre `ACTIVE`)."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(max_length=30)
    name: str = Field(max_length=100)
    description: str | None = None


class GlobalPaymentConditionTypeUpdate(PartialUpdate):
    """`PUT` parcial (D28): solo los campos que cambian; `version` opcional (D9)."""

    not_nullable = frozenset({"code", "name"})

    code: str | None = Field(default=None, max_length=30)
    name: str | None = Field(default=None, max_length=100)
    description: str | None = None


class VersionRequest(BaseModel):
    """Cuerpo de `deactivate` y `reactivate`: versión opcional; el cuerpo puede omitirse (D10)."""

    model_config = ConfigDict(extra="forbid")

    version: int | None = None


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
    version: int
