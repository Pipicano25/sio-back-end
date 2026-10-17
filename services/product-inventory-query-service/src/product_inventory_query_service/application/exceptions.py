"""Errores de aplicación del servicio de consultas (spec 022, `contracts/product-inventory-query-api.md` §5).

`api/errors.py` es el único módulo que asigna estados HTTP (Principio XII).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

OPERATIONAL_CONTEXT = "operational-context"
COMMERCIAL_RELATIONSHIP = "commercial-relationship"
PRODUCT_CATALOG = "product-catalog"
INVENTORY = "inventory"
KEYCLOAK = "keycloak"


class QueryServiceError(Exception):
    """Error de aplicación con código estable (D12 interina)."""

    code = "INTERNAL_ERROR"
    title = "Error interno"

    def __init__(
        self,
        message: str,
        *,
        errors: Sequence[dict[str, Any]] = (),
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.errors = tuple(errors)
        self.context = dict(context or {})


class ValidationFailedError(QueryServiceError):
    code = "VALIDATION_ERROR"
    title = "Solicitud inválida"


class InvalidCursorError(QueryServiceError):
    """Cursor malformado, alterado, de otra empresa o de otro endpoint (FR-022-149, pasos 2 a 6).

    Siempre se responde con el mismo mensaje; la causa solo va al log.
    """

    code = "INVALID_CURSOR"
    title = "Cursor inválido"
    PUBLIC_MESSAGE = "El cursor no es válido. Repita la consulta sin cursor."

    def __init__(self, cause: str) -> None:
        super().__init__(self.PUBLIC_MESSAGE)
        self.cause = cause


class NotFoundError(QueryServiceError):
    """Empresa inexistente, sin membresía ACTIVE o sucursal de otra empresa (FR-022-11, FR-022-22)."""

    code = "NOT_FOUND"
    title = "Recurso no encontrado"


class ForbiddenFilterError(QueryServiceError):
    """Filtro de un bloque que el usuario no puede ver (FR-022-14)."""

    code = "FORBIDDEN"
    title = "Acceso denegado"


class DependencyUnavailableError(QueryServiceError):
    """Dependencia caída, lenta, con respuesta inválida o que rechazó la cuenta técnica (FR-022-71, FR-022-72).

    La dependencia y la causa solo se registran en el log; la respuesta nunca es parcial.
    """

    code = "DEPENDENCY_UNAVAILABLE"
    title = "Dependencia no disponible"
    PUBLIC_MESSAGE = "Una dependencia del servicio no está disponible. Intente de nuevo más tarde."

    def __init__(self, provider: str, operation: str, cause: str) -> None:
        super().__init__(self.PUBLIC_MESSAGE)
        self.provider = provider
        self.operation = operation
        self.cause = cause
