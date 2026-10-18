"""Errores de aplicación de business-reporting-service (spec 023, `contracts/business-reporting-api.md` §5).

`api/errors.py` es el único módulo que asigna estados HTTP (Principio XII).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

OPERATIONAL_CONTEXT = "operational-context"
SALES = "sales"
PURCHASE = "purchase"
INVENTORY = "inventory"
COMMERCIAL_RELATIONSHIP = "commercial-relationship"
PRODUCT_CATALOG = "product-catalog"


class ReportingError(Exception):
    """Error de aplicación con código estable (D12 interina)."""

    code = "INTERNAL_ERROR"
    title = "Error interno"

    def __init__(self, message: str, *, errors: Sequence[dict[str, Any]] = (), context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = tuple(errors)
        self.context = dict(context or {})


class ValidationFailedError(ReportingError):
    code = "VALIDATION_ERROR"
    title = "Solicitud inválida"


class NotFoundError(ReportingError):
    """Empresa inexistente, sin membresía `ACTIVE` o sucursal de otra empresa (sin distinguir)."""

    code = "NOT_FOUND"
    title = "Recurso no encontrado"
    PUBLIC_MESSAGE = "La empresa o la sucursal no existe o no tiene acceso."

    def __init__(self) -> None:
        super().__init__(self.PUBLIC_MESSAGE)


class OwnerForbiddenError(ReportingError):
    """El servicio propietario rechazó el token del usuario (`403`): le falta su permiso de lectura.

    La respuesta es el mismo `403` genérico de `sio-auth`, sin revelar qué permiso falta (D3); el servicio y la
    operación solo se registran en el log.
    """

    code = "FORBIDDEN"
    title = "Acceso denegado"

    def __init__(self, provider: str, operation: str) -> None:
        from sio_auth import FORBIDDEN_DETAIL

        super().__init__(FORBIDDEN_DETAIL)
        self.provider = provider
        self.operation = operation


class UnauthenticatedError(ReportingError):
    """El propietario rechazó el token del usuario con `401` (p. ej. venció durante el reporte)."""

    code = "UNAUTHENTICATED"
    title = "No autenticado"

    def __init__(self) -> None:
        super().__init__("El token de acceso no es válido o venció. Solicite uno nuevo.")


class DependencyUnavailableError(ReportingError):
    """Dependencia caída, lenta, con respuesta inválida o incidente de integridad (FR-023-14, FR-023-32).

    La dependencia y la causa solo se registran en el log; nunca se entrega un reporte parcial como completo.
    """

    code = "DEPENDENCY_UNAVAILABLE"
    title = "Dependencia no disponible"
    PUBLIC_MESSAGE = "Una dependencia del servicio no está disponible. Intente de nuevo más tarde."

    def __init__(self, provider: str, operation: str, cause: str) -> None:
        super().__init__(self.PUBLIC_MESSAGE)
        self.provider = provider
        self.operation = operation
        self.cause = cause
