"""Excepciones funcionales de Payment Reference Service."""

from payment_reference_service.domain.global_payment_condition_types import (  # noqa: F401
    InvalidStatusTransitionError,
)

VERSION_CONFLICT_MESSAGE = (
    "El registro fue modificado por otra operación. Consulte nuevamente antes de modificarlo."
)


class GlobalPaymentConditionTypeNotFoundError(Exception):
    """Indica que el tipo de condición de pago solicitado no existe."""


class GlobalPaymentConditionTypeConflictError(Exception):
    """Indica un conflicto de integridad al guardar el registro."""


class GlobalPaymentMethodNotFoundError(Exception):
    """Indica que el método global de pago solicitado no existe."""


class GlobalPaymentMethodConflictError(Exception):
    """Indica un conflicto de integridad al guardar un método de pago."""


class GlobalPaymentConditionTypeVersionConflictError(Exception):
    """La versión esperada no coincide con la vigente o otra operación ganó la carrera (FR-015)."""
