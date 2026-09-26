"""Excepción base del servicio y errores de validación del dominio.

Son agnósticas del transporte (Principio XII): exponen un `code` estable, un
mensaje y, cuando aplica, el campo afectado. El estado HTTP lo asigna
exclusivamente `api/errors.py`.
"""

from typing import Any


class OperationalContextError(Exception):
    """Base de las excepciones de dominio y aplicación del servicio.

    Attributes:
        code: Código estable sin prefijo (p. ej. `GEOGRAPHY_INCOHERENT`).
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


class DomainValidationError(OperationalContextError, ValueError):
    """Un valor no cumple una regla de formato o de dominio.

    Hereda de `ValueError` para que los validadores de Pydantic lo conviertan
    en un error de validación por campo (`422 VALIDATION_ERROR`).
    """

    code = "VALIDATION_ERROR"
    title = "Solicitud inválida"
    default_message = "La solicitud contiene datos inválidos."


class GeographyParentRequiredError(OperationalContextError):
    """Se informó división o ciudad sin el país (FR-031)."""

    code = "GEOGRAPHY_PARENT_REQUIRED"
    title = "Falta el nivel geográfico superior"
    default_message = (
        "Si se informa la división administrativa o la ciudad, también debe "
        "informarse el país."
    )
