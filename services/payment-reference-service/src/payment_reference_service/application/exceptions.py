"""Excepciones funcionales de Payment Reference Service."""


class GlobalPaymentConditionTypeNotFoundError(Exception):
    """Indica que el tipo de condición de pago solicitado no existe."""


class GlobalPaymentConditionTypeConflictError(Exception):
    """Indica un conflicto de integridad al guardar el registro."""

class GlobalPaymentMethodNotFoundError(Exception):
    """Indica que el método global de pago solicitado no existe."""


class GlobalPaymentMethodConflictError(Exception):
    """Indica un conflicto de integridad al guardar un método de pago."""
