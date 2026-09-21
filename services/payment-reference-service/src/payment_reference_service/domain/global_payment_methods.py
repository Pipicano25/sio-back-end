"""Dominio de métodos globales de pago."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class PaymentMethodType(StrEnum):
    """Tipos funcionales permitidos para un método global de pago."""

    CASH = "CASH"
    BANK = "BANK"
    CARD = "CARD"
    WALLET = "WALLET"
    CHECK = "CHECK"
    OTHER = "OTHER"


class PaymentMethodStatus(StrEnum):
    """Estados permitidos para un método global de pago."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True, slots=True)
class GlobalPaymentMethod:
    """Representa un método global de pago.

    Attributes:
        id: Identificador único del registro.
        code: Código estable del método de pago.
        name: Nombre visible del método.
        method_type: Clasificación funcional del método.
        requires_reference: Indica si normalmente requiere una referencia externa.
        status: Estado funcional del registro.
        created_by: Subject OIDC del usuario que creó el registro.
        updated_by: Subject OIDC del último usuario que modificó el registro.
        created_at: Fecha y hora de creación.
        updated_at: Fecha y hora de última modificación.
    """

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
