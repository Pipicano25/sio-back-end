"""Dominio de tipos globales de condición de pago."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class PaymentConditionStatus(StrEnum):
    """Estados permitidos para una condición global de pago."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True, slots=True)
class GlobalPaymentConditionType:
    """Representa un tipo global de condición de pago.

    Attributes:
        id: Identificador único del registro.
        code: Código estable de la condición de pago.
        name: Nombre visible de la condición.
        description: Descripción funcional opcional.
        status: Estado funcional del registro.
        created_by: Subject OIDC del usuario que creó el registro.
        updated_by: Subject OIDC del último usuario que lo modificó.
        created_at: Fecha y hora de creación.
        updated_at: Fecha y hora de última actualización.
        version: Versión para concurrencia optimista (inicia en 1).
    """

    id: UUID
    code: str
    name: str
    description: str | None
    status: PaymentConditionStatus
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
    version: int = 1


class InvalidStatusTransitionError(Exception):
    """La acción no aplica al estado actual del tipo de condición de pago (FR-014)."""


def deactivated_status(current: PaymentConditionStatus) -> PaymentConditionStatus:
    """Estado tras inactivar: solo `ACTIVE` → `INACTIVE` (FR-012).

    Raises:
        InvalidStatusTransitionError: Si el tipo ya está inactivo.
    """
    if current is not PaymentConditionStatus.ACTIVE:
        raise InvalidStatusTransitionError("El tipo de condición de pago ya está inactivo.")
    return PaymentConditionStatus.INACTIVE


def reactivated_status(current: PaymentConditionStatus) -> PaymentConditionStatus:
    """Estado tras reactivar: solo `INACTIVE` → `ACTIVE` (FR-013).

    Raises:
        InvalidStatusTransitionError: Si el tipo ya está activo.
    """
    if current is not PaymentConditionStatus.INACTIVE:
        raise InvalidStatusTransitionError("El tipo de condición de pago ya está activo.")
    return PaymentConditionStatus.ACTIVE
