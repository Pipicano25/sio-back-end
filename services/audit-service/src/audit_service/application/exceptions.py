"""Excepciones de aplicación de Audit Service (Principio XII).

Solo llevan `code`, título, mensaje y campos; el estado HTTP lo asigna
`api/errors.py` (`contracts/errors.md`). Ninguna lleva valores del evento.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class AuditError(Exception):
    """Base de las excepciones de aplicación."""

    code = "INTERNAL_ERROR"
    title = "Error"

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        errors: Sequence[dict[str, str]] = (),
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.errors = tuple(errors)
        self.context = context or {}


class ValidationFailedError(AuditError):
    """Uno o varios campos no cumplen el contrato del evento (`422`)."""

    code = "VALIDATION_ERROR"
    title = "Solicitud inválida"


class EventIdConflictError(AuditError):
    """`event_id` existente con contenido o emisor distinto (`409`)."""

    code = "EVENT_ID_CONFLICT"
    title = "Conflicto de event_id"


class NotFoundError(AuditError):
    """Recurso inexistente o fuera del alcance del usuario (`404`)."""

    code = "NOT_FOUND"
    title = "Recurso no encontrado"


class OperationalAccessDeniedError(AuditError):
    """Operational Context denegó la evaluación de acceso del usuario (`403`)."""

    code = "OPERATIONAL_ACCESS_DENIED"
    title = "Acceso operativo denegado"


class ForbiddenError(AuditError):
    """Operación no permitida para la identidad (`403`, sin revelar el motivo)."""

    code = "FORBIDDEN"
    title = "Acceso denegado"


class DependencyUnavailableError(AuditError):
    """Un proveedor no está disponible (`503` con `dependency`)."""

    code = "DEPENDENCY_UNAVAILABLE"
    title = "Dependencia no disponible"

    def __init__(self, provider: str, *, operation: str, cause: str) -> None:
        super().__init__(
            "Un servicio requerido no está disponible temporalmente. Intente de nuevo más tarde."
        )
        self.provider = provider
        self.operation = operation
        self.cause = cause
