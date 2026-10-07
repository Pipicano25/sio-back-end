"""Excepciones de aplicación de Inventory Service (Principio XII).

Solo llevan `code`, título, mensaje y detalle por campo; el estado HTTP lo asigna
`api/errors.py` (`contracts/errors.md`).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

DATABASE = "database"
OPERATIONAL_CONTEXT = "operational-context"
COMMERCIAL_RELATIONSHIP = "commercial-relationship"


def field_error(field: str, code: str, message: str) -> dict[str, str]:
    """Elemento de `errors[]` (D13 provisional)."""
    return {"field": field, "message": message, "code": code}


class InventoryError(Exception):
    """Base de las excepciones de aplicación."""

    code = "INTERNAL_ERROR"
    title = "Error"

    def __init__(
        self,
        message: str,
        *,
        errors: Sequence[dict[str, str]] = (),
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.errors = tuple(errors)
        self.context = context or {}


class ValidationFailedError(InventoryError):
    """Formato o referencia inválida (`422`); `errors[].code` precisa la causa."""

    code = "VALIDATION_ERROR"
    title = "Solicitud inválida"

    def __init__(self, errors: Sequence[dict[str, str]]) -> None:
        super().__init__("La solicitud contiene datos inválidos.", errors=errors)


class OperationKeyConflictError(InventoryError):
    """Clave usada con otra solicitud o por otro cliente (`409`; R-03)."""

    code = "OPERATION_KEY_CONFLICT"
    title = "Conflicto de clave de operación"

    def __init__(self) -> None:
        super().__init__(
            "La clave de operación ya se usó con una solicitud distinta. Use una clave nueva "
            "para una solicitud nueva o repita exactamente la solicitud original."
        )


class InsufficientStockError(InventoryError):
    """La operación dejaría algún saldo negativo (`409`; DS-04)."""

    code = "INSUFFICIENT_STOCK"
    title = "Saldo insuficiente"

    def __init__(self, shortages: Sequence[dict[str, Any]]) -> None:
        super().__init__(
            "No hay saldo suficiente para aplicar la operación; no se aplicó ninguna línea.",
            context={"shortages": list(shortages)},
        )


class AlreadyReversedError(InventoryError):
    """La operación ya tiene reverso (`409`; FR-032)."""

    code = "ALREADY_REVERSED"
    title = "Operación ya revertida"

    def __init__(self) -> None:
        super().__init__("La operación ya fue revertida.")


class ReversalNotAllowedError(InventoryError):
    """Se pidió revertir un reverso (`409`; FR-032)."""

    code = "REVERSAL_NOT_ALLOWED"
    title = "Reverso no permitido"

    def __init__(self) -> None:
        super().__init__("Un reverso no se puede revertir.")


class NotFoundError(InventoryError):
    """Recurso inexistente o fuera del alcance (`404`)."""

    code = "NOT_FOUND"
    title = "Recurso no encontrado"

    def __init__(self) -> None:
        super().__init__("El recurso solicitado no existe o no está disponible para su usuario.")


class OperationalAccessDeniedError(InventoryError):
    """Operational Context denegó la evaluación de acceso del usuario (`403`)."""

    code = "OPERATIONAL_ACCESS_DENIED"
    title = "Acceso operativo denegado"

    def __init__(self) -> None:
        super().__init__(
            "No tiene permiso para consultar el acceso operativo requerido. Solicite acceso al "
            "administrador del sistema indicando el trace_id."
        )


class DependencyUnavailableError(InventoryError):
    """Un proveedor o la base no están disponibles (`503` con `dependency`)."""

    code = "DEPENDENCY_UNAVAILABLE"
    title = "Dependencia no disponible"

    def __init__(self, provider: str, *, operation: str, cause: str) -> None:
        super().__init__(
            "Un servicio requerido no está disponible temporalmente. Intente de nuevo más tarde."
        )
        self.provider = provider
        self.operation = operation
        self.cause = cause


# Fase B (013): `specs/013-inventory-complementary/contracts/errors.md` -------------


class BranchAccessDeniedError(InventoryError):
    """Miembro sin asignación `ACTIVE` a la sucursal, o sucursal/empresa inactiva (`403`; R-09, DS-14)."""

    code = "BRANCH_ACCESS_DENIED"
    title = "Acceso a la sucursal denegado"

    def __init__(self) -> None:
        super().__init__(
            "No tiene una asignación activa a la sucursal, o la sucursal o la empresa no están activas. "
            "Solicite la asignación al administrador de la empresa."
        )


class EntryLayerConsumedError(InventoryError):
    """La capa FIFO de la entrada ya fue consumida total o parcialmente (`409`; DS-16)."""

    code = "ENTRY_LAYER_CONSUMED"
    title = "Capa de la entrada consumida"

    def __init__(self) -> None:
        super().__init__(
            "La entrada no se puede revertir porque sus unidades ya fueron consumidas. Anule antes las ventas "
            "que las consumieron o registre un ajuste."
        )


class OutputNotValuedError(InventoryError):
    """Salida anterior a la valoración, sin consumos FIFO (`409`; DS-17)."""

    code = "OUTPUT_NOT_VALUED"
    title = "Salida sin valoración"

    def __init__(self) -> None:
        super().__init__(
            "La salida se aplicó antes de la valoración FIFO y no se puede revertir. Corrija el inventario con "
            "un ajuste positivo con costo."
        )


class CountAlreadyInProgressError(InventoryError):
    code = "COUNT_ALREADY_IN_PROGRESS"
    title = "Conteo en curso"

    def __init__(self) -> None:
        super().__init__("Ya hay un conteo en curso en la sucursal.")


class CountNotInProgressError(InventoryError):
    code = "COUNT_NOT_IN_PROGRESS"
    title = "Conteo no en curso"

    def __init__(self) -> None:
        super().__init__("El conteo no está en curso.")


class InvalidCountTransitionError(InventoryError):
    code = "INVALID_COUNT_TRANSITION"
    title = "Transición de conteo no permitida"

    def __init__(self) -> None:
        super().__init__("La transición no está permitida desde el estado actual del conteo.")


class VersionConflictError(InventoryError):
    """`version` desactualizada (`409`; Principio VII)."""

    code = "VERSION_CONFLICT"
    title = "Conflicto de versión"

    def __init__(self) -> None:
        super().__init__("El recurso cambió desde la última consulta. Vuelva a consultarlo e intente de nuevo.")


class PolicyAlreadyExistsError(InventoryError):
    code = "POLICY_ALREADY_EXISTS"
    title = "Política ya registrada"

    def __init__(self) -> None:
        super().__init__("La empresa ya tiene una política de inventario; actualícela.")


class ActivePolicyExistsError(InventoryError):
    code = "ACTIVE_POLICY_EXISTS"
    title = "Política activa existente"

    def __init__(self) -> None:
        super().__init__("Ya existe una política activa para el producto en la sucursal; inactívela primero.")


class ValuationInvariantError(RuntimeError):
    """Σ capas abiertas ≠ saldo antes del `COMMIT` (RC-15): error interno, la transacción se revierte."""
