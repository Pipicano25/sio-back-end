"""Excepciones de aplicación de Sales Service (Principio XII; `contracts/errors.md`).

Solo llevan `code`, título, mensaje, detalle por campo y contexto; el estado HTTP lo
asigna `api/errors.py`. Regla P-03: referencia inexistente, de otra empresa, no
resoluble o incoherente → `422 VALIDATION_ERROR`; referencia existente cuyo estado o
configuración impide usarla → `409 REFERENCES_NOT_ELIGIBLE`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

DATABASE = "database"
OPERATIONAL_CONTEXT = "operational-context"
COMMERCIAL_RELATIONSHIP = "commercial-relationship"
PRODUCT_CATALOG = "product-catalog"
PARTY_IDENTITY = "party-identity"
INVENTORY = "inventory"
PAYMENT_REFERENCE = "payment-reference"


def field_error(field: str, code: str, message: str, *, line_number: int | None = None) -> dict[str, Any]:
    """Elemento de `errors[]` (D13 provisional)."""
    error: dict[str, Any] = {"field": field, "message": message, "code": code}
    if line_number is not None:
        error["line_number"] = line_number
    return error


class SalesError(Exception):
    """Base de las excepciones de aplicación."""

    code = "INTERNAL_ERROR"
    title = "Error"

    def __init__(
        self,
        message: str,
        *,
        errors: Sequence[Mapping[str, Any]] = (),
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.errors = tuple(dict(error) for error in errors)
        self.context = context or {}

    def to_record(self) -> dict[str, Any]:
        """Forma persistible en `sale_operations.error_details` para repetir el error (R-04)."""
        return {
            "code": self.code,
            "title": self.title,
            "message": self.message,
            "errors": list(self.errors),
            "context": dict(self.context),
        }


class StoredError(SalesError):
    """Error original de una operación `FAILED`, repetido ante la misma clave (R-04)."""

    def __init__(self, record: Mapping[str, Any]) -> None:
        super().__init__(
            str(record.get("message", "")), errors=record.get("errors") or (), context=record.get("context") or {}
        )
        self.code = str(record.get("code", "INTERNAL_ERROR"))
        self.title = str(record.get("title", "Error"))


class ValidationFailedError(SalesError):
    code = "VALIDATION_ERROR"
    title = "Solicitud inválida"

    def __init__(self, errors: Sequence[Mapping[str, Any]]) -> None:
        super().__init__("La solicitud contiene datos inválidos.", errors=errors)


class ReferencesNotEligibleError(SalesError):
    code = "REFERENCES_NOT_ELIGIBLE"
    title = "Referencias no aptas"

    def __init__(self, errors: Sequence[Mapping[str, Any]]) -> None:
        super().__init__(
            "Una o más referencias existen, pero su estado o configuración actual impide usarlas en la venta.",
            errors=errors,
        )


class NotFoundError(SalesError):
    code = "NOT_FOUND"
    title = "Recurso no encontrado"

    def __init__(self) -> None:
        super().__init__("El recurso solicitado no existe o no está disponible para su usuario.")


class OperationalAccessDeniedError(SalesError):
    code = "OPERATIONAL_ACCESS_DENIED"
    title = "Acceso operativo denegado"

    def __init__(self) -> None:
        super().__init__(
            "No tiene permiso para consultar el acceso operativo requerido. Solicite acceso al "
            "administrador del sistema indicando el trace_id."
        )


class BranchAccessDeniedError(SalesError):
    code = "BRANCH_ACCESS_DENIED"
    title = "Acceso a la sucursal denegado"

    def __init__(self) -> None:
        super().__init__(
            "No tiene una asignación activa a la sucursal de la venta, o la sucursal o la empresa no están "
            "activas. Solicite la asignación al administrador de la empresa."
        )


class VersionConflictError(SalesError):
    code = "VERSION_CONFLICT"
    title = "Conflicto de versión"

    def __init__(self) -> None:
        super().__init__("El recurso cambió desde la última consulta. Vuelva a consultarlo e intente de nuevo.")


class InvalidStatusError(SalesError):
    code = "INVALID_STATUS"
    title = "Estado no permitido"

    def __init__(self, status: str) -> None:
        super().__init__(
            f"La acción no está permitida para una venta en estado {status}.", context={"status": status}
        )


class OperationInProgressError(SalesError):
    code = "OPERATION_IN_PROGRESS"
    title = "Operación en curso"

    def __init__(self, operation_id: Any) -> None:
        super().__init__(
            "La venta tiene una confirmación o anulación en curso. Repita la solicitud con su clave de "
            "idempotencia o espere a que termine.",
            context={"operation_id": str(operation_id)},
        )


class IdempotencyKeyConflictError(SalesError):
    code = "IDEMPOTENCY_KEY_CONFLICT"
    title = "Conflicto de clave de idempotencia"

    def __init__(self) -> None:
        super().__init__(
            "La clave de idempotencia ya se usó para otra solicitud. Use una clave nueva para una solicitud nueva."
        )


class SaleWithoutLinesError(SalesError):
    code = "SALE_WITHOUT_LINES"
    title = "Venta sin líneas"

    def __init__(self) -> None:
        super().__init__("La venta debe tener al menos una línea para confirmarse.")


class SequenceNotConfiguredError(SalesError):
    code = "SEQUENCE_NOT_CONFIGURED"
    title = "Secuencia no configurada"

    def __init__(self) -> None:
        super().__init__(
            "No hay una secuencia de numeración activa para la sucursal ni para la empresa. Configure una "
            "secuencia de ventas antes de confirmar."
        )


class SequenceExhaustedError(SalesError):
    code = "SEQUENCE_EXHAUSTED"
    title = "Secuencia agotada"

    def __init__(self, period_key: str = "") -> None:
        super().__init__(
            "La secuencia alcanzó su número máximo para el período de la venta.",
            context={"period_key": period_key},
        )


class SequenceInUseError(SalesError):
    code = "SEQUENCE_IN_USE"
    title = "Secuencia en uso"

    def __init__(self, fields: Sequence[str] = ()) -> None:
        super().__init__(
            "La secuencia ya asignó números: no se pueden cambiar su formato, serie, política ni alcance.",
            context={"fields": list(fields)},
        )


class SequenceAlreadyActiveError(SalesError):
    code = "SEQUENCE_ALREADY_ACTIVE"
    title = "Secuencia activa existente"

    def __init__(self) -> None:
        super().__init__(
            "Ya existe una secuencia activa para la empresa, la sucursal y el tipo de documento. Desactívela antes."
        )


class InventoryRejectedError(SalesError):
    code = "INVENTORY_REJECTED"
    title = "Inventory rechazó la operación"

    def __init__(self, inventory_code: str | None, inventory_status: int | None = None) -> None:
        super().__init__(
            "Inventory rechazó la operación de la venta.",
            context={"details": {"inventory_code": inventory_code, "inventory_status": inventory_status}},
        )


class OperationNotAppliedError(SalesError):
    """La conciliación comprobó que Inventory nunca aplicó la operación (`409`; D-01, `errors.md`)."""

    code = "OPERATION_NOT_APPLIED"
    title = "Operación no aplicada"

    def __init__(self) -> None:
        super().__init__(
            "La operación no se aplicó en Inventory y quedó cerrada por la conciliación. Repita la acción con una "
            "clave de idempotencia nueva."
        )


class PricesChangedError(SalesError):
    """El precio, la lista o el ítem vigentes difieren de lo guardado (DS-05; `409`, sin efectos)."""

    code = "PRICES_CHANGED"
    title = "Precios cambiados"

    def __init__(self, errors: Sequence[Mapping[str, Any]]) -> None:
        super().__init__(
            "El precio aplicable de una o más líneas cambió desde que se guardaron. Actualice esas líneas y "
            "confirme de nuevo.",
            errors=errors,
        )


class InsufficientStockError(SalesError):
    """Alguna línea no tiene existencias suficientes en la sucursal (consulta previa o Inventory; `409`)."""

    code = "INSUFFICIENT_STOCK"
    title = "Existencias insuficientes"

    def __init__(self, shortages: Sequence[Mapping[str, Any]]) -> None:
        super().__init__(
            "No hay existencias suficientes en la sucursal para una o más líneas. La venta no se confirmó.",
            context={"shortages": [dict(item) for item in shortages]},
        )


class DependencyUnavailableError(SalesError):
    """Un proveedor o la base no están disponibles (`503` con `dependency`)."""

    code = "DEPENDENCY_UNAVAILABLE"
    title = "Dependencia no disponible"

    def __init__(self, provider: str, *, operation: str, cause: str, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            "Un servicio requerido no está disponible temporalmente. Intente de nuevo más tarde.", context=context
        )
        self.provider = provider
        self.operation = operation
        self.cause = cause
