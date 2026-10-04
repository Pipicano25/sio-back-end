"""Excepción base del servicio y errores de validación del dominio.

Son agnósticas del transporte (Principio XII): exponen un `code` estable, un
mensaje y, cuando aplica, el campo afectado. El estado HTTP lo asigna
exclusivamente `api/errors.py`.
"""

from typing import Any


class CommercialRelationshipError(Exception):
    """Base de las excepciones de dominio y aplicación del servicio.

    Attributes:
        code: Código estable sin prefijo (p. ej. `DUPLICATE_ADOPTION`).
        title: Título breve del error.
        message: Explicación para el usuario, sin detalles internos.
        field: Campo de la solicitud al que se refiere el error, si aplica.
        context: Datos adicionales seguros de exponer.
    """

    code = "INTERNAL_ERROR"
    title = "Error interno"
    default_message = "Ocurrió un error inesperado."

    def __init__(
        self,
        message: str | None = None,
        *,
        field: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.field = field
        self.context = context or {}
        super().__init__(self.message)


class CurrencyNotSupportedError(CommercialRelationshipError):
    """La moneda no pertenece a la lista cerrada de FR-014a."""

    code = "CURRENCY_NOT_SUPPORTED"
    title = "Moneda no admitida"
    default_message = "La moneda indicada no está en la lista de monedas admitidas."


class PriceScaleNotAllowedError(CommercialRelationshipError):
    """El precio tiene más decimales que los de su moneda (FR-014)."""

    code = "PRICE_SCALE_NOT_ALLOWED"
    title = "Decimales no admitidos"
    default_message = "El precio tiene más decimales de los que admite su moneda."


class InventoryFlagsInvalidError(CommercialRelationshipError):
    """Lotes sin control de inventario o vencimiento sin lotes (RN-03)."""

    code = "INVENTORY_FLAGS_INVALID"
    title = "Configuración de inventario inválida"
    default_message = "La combinación de banderas de inventario no es válida."


class CustomerIdentityMismatchError(CommercialRelationshipError):
    """El tipo de cliente no corresponde con la identidad indicada (FR-020)."""

    code = "CUSTOMER_IDENTITY_MISMATCH"
    title = "Identidad del cliente inválida"
    default_message = (
        "Un cliente PERSON exige person_identity_id y un cliente ORGANIZATION exige "
        "organization_identity_id; nunca ambos."
    )


class ContactPersonNotAllowedError(CommercialRelationshipError):
    """Un cliente persona no admite persona de contacto preferida (FR-022)."""

    code = "CONTACT_PERSON_NOT_ALLOWED"
    title = "Contacto no permitido"
    default_message = "Solo los clientes ORGANIZATION admiten persona de contacto preferida."


class InvalidStatusTransitionError(CommercialRelationshipError):
    """La acción de estado no es válida desde el estado actual (FR-033)."""

    code = "INVALID_STATUS_TRANSITION"
    title = "Transición de estado inválida"
    default_message = "La acción no es válida para el estado actual del registro."
