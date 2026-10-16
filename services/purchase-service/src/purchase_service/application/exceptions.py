"""Excepciones de aplicación de Purchase Service (Principio XII; `contracts/errors.md`).

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
PAYMENT_REFERENCE = "payment-reference"
INVENTORY = "inventory"


def field_error(field: str, code: str, message: str, *, line_number: int | None = None) -> dict[str, Any]:
    """Elemento de `errors[]` (D13 provisional)."""
    error: dict[str, Any] = {"field": field, "message": message, "code": code}
    if line_number is not None:
        error["line_number"] = line_number
    return error


class PurchaseError(Exception):
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
        """Forma persistible en `purchase_operations.error_details` para repetir el error (R-04)."""
        return {
            "code": self.code,
            "title": self.title,
            "message": self.message,
            "errors": list(self.errors),
            "context": dict(self.context),
        }


class StoredError(PurchaseError):
    """Error original de una operación `FAILED`, repetido ante la misma clave (R-04)."""

    def __init__(self, record: Mapping[str, Any]) -> None:
        super().__init__(
            str(record.get("message", "")), errors=record.get("errors") or (), context=record.get("context") or {}
        )
        self.code = str(record.get("code", "INTERNAL_ERROR"))
        self.title = str(record.get("title", "Error"))


class ValidationFailedError(PurchaseError):
    code = "VALIDATION_ERROR"
    title = "Solicitud inválida"

    def __init__(self, errors: Sequence[Mapping[str, Any]]) -> None:
        super().__init__("La solicitud contiene datos inválidos.", errors=errors)


class ReferencesNotEligibleError(PurchaseError):
    code = "REFERENCES_NOT_ELIGIBLE"
    title = "Referencias no aptas"

    def __init__(self, errors: Sequence[Mapping[str, Any]]) -> None:
        super().__init__(
            "Una o más referencias existen, pero su estado o configuración actual impide usarlas en la compra.",
            errors=errors,
        )


class NotFoundError(PurchaseError):
    code = "NOT_FOUND"
    title = "Recurso no encontrado"

    def __init__(self) -> None:
        super().__init__("El recurso solicitado no existe o no está disponible para su usuario.")


class OperationalAccessDeniedError(PurchaseError):
    code = "OPERATIONAL_ACCESS_DENIED"
    title = "Acceso operativo denegado"

    def __init__(self) -> None:
        super().__init__(
            "No tiene permiso para consultar el acceso operativo requerido. Solicite acceso al "
            "administrador del sistema indicando el trace_id."
        )


class BranchAccessDeniedError(PurchaseError):
    code = "BRANCH_ACCESS_DENIED"
    title = "Acceso a la sucursal denegado"

    def __init__(self) -> None:
        super().__init__(
            "No tiene una asignación activa a la sucursal de la compra, o la sucursal o la empresa no están "
            "activas. Solicite la asignación al administrador de la empresa."
        )


class VersionConflictError(PurchaseError):
    code = "VERSION_CONFLICT"
    title = "Conflicto de versión"

    def __init__(self) -> None:
        super().__init__("El recurso cambió desde la última consulta. Vuelva a consultarlo e intente de nuevo.")


class InvalidStatusError(PurchaseError):
    code = "INVALID_STATUS"
    title = "Estado no permitido"

    def __init__(self, status: str) -> None:
        super().__init__(
            f"La acción no está permitida para una compra en estado {status}.", context={"status": status}
        )


class OperationInProgressError(PurchaseError):
    code = "OPERATION_IN_PROGRESS"
    title = "Operación en curso"

    def __init__(self, operation_id: Any) -> None:
        super().__init__(
            "La compra tiene una confirmación o anulación en curso. Repita la solicitud con su clave de "
            "idempotencia o espere a que termine.",
            context={"operation_id": str(operation_id)},
        )


class IdempotencyKeyConflictError(PurchaseError):
    code = "IDEMPOTENCY_KEY_CONFLICT"
    title = "Conflicto de clave de idempotencia"

    def __init__(self) -> None:
        super().__init__(
            "La clave de idempotencia ya se usó para otra solicitud. Use una clave nueva para una solicitud nueva."
        )


class PurchaseWithoutLinesError(PurchaseError):
    code = "PURCHASE_WITHOUT_LINES"
    title = "Compra sin líneas"

    def __init__(self) -> None:
        super().__init__("La compra debe tener al menos una línea para confirmarse.")


class SequenceNotConfiguredError(PurchaseError):
    code = "SEQUENCE_NOT_CONFIGURED"
    title = "Secuencia no configurada"

    def __init__(self) -> None:
        super().__init__(
            "No hay una secuencia de numeración activa para la sucursal ni para la empresa. Configure una "
            "secuencia de compras antes de confirmar."
        )


class SequenceExhaustedError(PurchaseError):
    code = "SEQUENCE_EXHAUSTED"
    title = "Secuencia agotada"

    def __init__(self, period_key: str = "") -> None:
        super().__init__(
            "La secuencia alcanzó su número máximo para el período de la compra.",
            context={"period_key": period_key},
        )


class SequenceInUseError(PurchaseError):
    code = "SEQUENCE_IN_USE"
    title = "Secuencia en uso"

    def __init__(self, fields: Sequence[str] = ()) -> None:
        super().__init__(
            "La secuencia ya asignó números: no se pueden cambiar su formato, serie, política ni alcance.",
            context={"fields": list(fields)},
        )


class SequenceAlreadyActiveError(PurchaseError):
    code = "SEQUENCE_ALREADY_ACTIVE"
    title = "Secuencia activa existente"

    def __init__(self) -> None:
        super().__init__(
            "Ya existe una secuencia activa para la empresa, la sucursal y el tipo de documento. Desactívela antes."
        )


class InventoryAlreadyConsumedError(PurchaseError):
    code = "INVENTORY_ALREADY_CONSUMED"
    title = "Inventario ya consumido"

    def __init__(self) -> None:
        super().__init__(
            "La compra no se puede anular porque sus unidades ya fueron consumidas en Inventory. Anule antes las "
            "ventas que las consumieron o solicite un ajuste."
        )


class InventoryRejectedError(PurchaseError):
    code = "INVENTORY_REJECTED"
    title = "Inventory rechazó la operación"

    def __init__(self, inventory_code: str | None, inventory_status: int | None = None) -> None:
        super().__init__(
            "Inventory rechazó la operación de la compra.",
            context={"details": {"inventory_code": inventory_code, "inventory_status": inventory_status}},
        )


class OperationNotAppliedError(PurchaseError):
    """La conciliación comprobó que Inventory nunca aplicó la operación (`409`; D-01, `errors.md`)."""

    code = "OPERATION_NOT_APPLIED"
    title = "Operación no aplicada"

    def __init__(self) -> None:
        super().__init__(
            "La operación no se aplicó en Inventory y quedó cerrada por la conciliación. Repita la acción con una "
            "clave de idempotencia nueva."
        )


class PurchaseAlreadyReceivedError(PurchaseError):
    """Spec 020 (FR-020-02, RC-MVP-1): una compra se recibe una sola vez (`409`)."""

    code = "PURCHASE_ALREADY_RECEIVED"
    title = "Compra ya recibida"

    def __init__(self) -> None:
        super().__init__("La compra ya fue recibida: su entrada en Inventory existe y no se repite.")


class PurchaseNotReceivedError(PurchaseError):
    """Spec 020 (FR-020-07): los hitos de recepción exigen la recepción física registrada (`409`)."""

    code = "PURCHASE_NOT_RECEIVED"
    title = "Compra pendiente de recepción"

    def __init__(self, event_type: str) -> None:
        super().__init__(
            f"El hito {event_type} exige que la recepción física de la compra esté confirmada.",
            context={"event_type": event_type},
        )


class EventNotAllowedInStatusError(PurchaseError):
    code = "EVENT_NOT_ALLOWED_IN_STATUS"
    title = "Hito no permitido"

    def __init__(self, event_type: str, status: str) -> None:
        super().__init__(
            f"El hito {event_type} no se permite en una compra en estado {status}.",
            context={"event_type": event_type, "status": status},
        )


class DependencyUnavailableError(PurchaseError):
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


class PurchaseTaxNotConfiguredError(PurchaseError):
    """Spec 021 (FR-021-12, CP-31): hay líneas sin tasa de impuesto; el borrador se conserva (`409`)."""

    code = "PURCHASE_TAX_NOT_CONFIGURED"
    title = "Impuesto de compra sin configurar"

    def __init__(self, errors: Sequence[Mapping[str, Any]]) -> None:
        super().__init__(
            "Una o más líneas no tienen tasa de impuesto de compra: configure la tasa del producto (0 es válido) o "
            "ajuste la de la línea antes de confirmar.",
            errors=errors,
        )


class PurchaseTaxChangedError(PurchaseError):
    """Spec 021 (FR-021-12, DS-04, CP-65): la tasa predeterminada cambió desde que se guardó la línea (`409`)."""

    code = "PURCHASE_TAX_CHANGED"
    title = "Tasa de impuesto modificada"

    def __init__(self, errors: Sequence[Mapping[str, Any]]) -> None:
        super().__init__(
            "La tasa de impuesto predeterminada de uno o más productos cambió desde que se guardó la línea. Vuelva a "
            "guardar la línea para usar la tasa actual o ajústela a la de la factura.",
            errors=errors,
        )


class DuplicatePresentationInPurchaseError(PurchaseError):
    """Spec 021 (Historia 8, CP-29): la misma presentación aparece en dos líneas de la compra (`409`).

    Cada recepción entrega un solo costo por presentación a Commercial Relationship (serie contigua); por eso una compra
    no repite presentaciones. Lo garantiza también `uq_purchase_details_purchase_presentation`.
    """

    code = "DUPLICATE_PRESENTATION_IN_PURCHASE"
    title = "Presentación repetida en la compra"

    def __init__(self, errors: Sequence[Mapping[str, Any]]) -> None:
        super().__init__(
            "La misma presentación aparece en más de una línea: agrupe la cantidad en una sola línea.",
            errors=errors,
        )
