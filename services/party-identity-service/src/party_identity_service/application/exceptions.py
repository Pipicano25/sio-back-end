"""Excepciones de aplicación de Party Identity Service.

Son agnósticas del transporte (Principio XII): solo exponen un `code` estable,
un mensaje y, cuando aplica, contexto. El estado HTTP lo asigna exclusivamente
`api/errors.py`. Los mensajes nunca incluyen números de identificación ni
fechas de nacimiento completos (DS-09).
"""

from typing import Any

COUNTRY_VALIDATION_DENIED = "COUNTRY_VALIDATION_DENIED"
GEOGRAPHY_UNAVAILABLE = "GEOGRAPHY_UNAVAILABLE"


class PartyIdentityError(Exception):
    """Base de las excepciones de dominio y aplicación del servicio.

    Attributes:
        code: Código estable sin prefijo (p. ej. `DUPLICATE_IDENTIFICATION`).
        title: Título breve del error.
        message: Explicación para el usuario, sin datos sensibles completos.
        context: Datos adicionales seguros de exponer.
    """

    code = "INTERNAL_ERROR"
    title = "Error interno"
    default_message = "Ocurrió un error inesperado."

    def __init__(
        self,
        message: str | None = None,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.context = context or {}
        super().__init__(self.message)


class NotFoundError(PartyIdentityError):
    """El recurso solicitado no existe."""

    code = "NOT_FOUND"
    title = "Recurso no encontrado"
    default_message = "El recurso solicitado no existe."


class ImmutableFieldError(PartyIdentityError):
    """Se intentó modificar un campo inmutable."""

    code = "IMMUTABLE_FIELD"
    title = "Campo inmutable"
    default_message = "La solicitud intenta modificar un campo inmutable."


class RuleChangeRequiresNewVersionError(PartyIdentityError):
    """El cambio de patrón o edades exige crear una nueva versión de la regla."""

    code = "RULE_CHANGE_REQUIRES_NEW_VERSION"
    title = "Se requiere una nueva versión de la regla"
    default_message = (
        "El patrón y las edades de una regla no se modifican en sitio; "
        "cree una nueva versión de la regla."
    )


class InvalidNumberPatternError(PartyIdentityError):
    """El patrón de la regla no es una expresión regular válida."""

    code = "INVALID_NUMBER_PATTERN"
    title = "Patrón inválido"
    default_message = "El patrón de número no es una expresión regular válida."


class ExampleDoesNotMatchPatternError(PartyIdentityError):
    """El ejemplo de la regla no cumple su patrón."""

    code = "EXAMPLE_DOES_NOT_MATCH_PATTERN"
    title = "Ejemplo inválido"
    default_message = "El valor de ejemplo no cumple el patrón de la regla."


class InvalidAgeRangeError(PartyIdentityError):
    """El rango de edades de la regla no es coherente."""

    code = "INVALID_AGE_RANGE"
    title = "Rango de edad inválido"
    default_message = "max_age_years debe ser mayor o igual a min_age_years."


class InvalidValidityRangeError(PartyIdentityError):
    """El rango de vigencia de la regla no es coherente."""

    code = "INVALID_VALIDITY_RANGE"
    title = "Vigencia inválida"
    default_message = "valid_to debe ser posterior a valid_from."


class InvalidIdentificationNumberError(PartyIdentityError):
    """El número no cumple ninguna regla activa de la sigla."""

    code = "INVALID_IDENTIFICATION_NUMBER"
    title = "Número de identificación inválido"
    default_message = (
        "El número de identificación no cumple ninguna regla activa "
        "para la sigla indicada."
    )


class BirthDateRequiredError(PartyIdentityError):
    """La regla aplicable exige fecha de nacimiento."""

    code = "BIRTH_DATE_REQUIRED"
    title = "Fecha de nacimiento obligatoria"
    default_message = (
        "La fecha de nacimiento es obligatoria para validar el rango de "
        "edad del tipo de identificación."
    )


class AgeOutOfRangeError(PartyIdentityError):
    """La edad no cumple el rango de la regla aplicable."""

    code = "AGE_OUT_OF_RANGE"
    title = "Edad fuera de rango"
    default_message = (
        "La edad de la persona no cumple el rango permitido para el tipo "
        "de identificación."
    )


class BirthDateInFutureError(PartyIdentityError):
    """La fecha de nacimiento es posterior a hoy."""

    code = "BIRTH_DATE_IN_FUTURE"
    title = "Fecha de nacimiento futura"
    default_message = "La fecha de nacimiento no puede ser posterior a hoy."


class CountryNotFoundError(PartyIdentityError):
    """El país referenciado no existe en Geography Service."""

    code = "COUNTRY_NOT_FOUND"
    title = "País inexistente"
    default_message = "El país indicado no existe en Geography Service."


class DuplicateIdentificationError(PartyIdentityError):
    """Ya existe una identidad con el mismo país, tipo y número."""

    code = "DUPLICATE_IDENTIFICATION"
    title = "Identificación duplicada"
    default_message = (
        "Ya existe una identidad con el país, tipo y número de "
        "identificación indicados."
    )


class DuplicateActiveRuleError(PartyIdentityError):
    """Ya existe una regla activa para la misma llave."""

    code = "DUPLICATE_ACTIVE_RULE"
    title = "Regla activa duplicada"
    default_message = (
        "Ya existe una regla activa para el tipo de parte, país y tipo de "
        "identificación indicados."
    )


class VersionConflictError(PartyIdentityError):
    """La versión esperada está desactualizada."""

    code = "VERSION_CONFLICT"
    title = "Versión desactualizada"
    default_message = (
        "El registro fue modificado por otra operación. Consulte "
        "nuevamente antes de actualizar."
    )


class InvalidStatusTransitionError(PartyIdentityError):
    """La transición de estado no es válida para el estado actual."""

    code = "INVALID_STATUS_TRANSITION"
    title = "Transición de estado inválida"
    default_message = "La operación no es válida para el estado actual del recurso."


class DependencyUnavailableError(PartyIdentityError):
    """No fue posible validar contra una dependencia externa.

    Attributes:
        cause: Causa interna solo para logs (`COUNTRY_VALIDATION_DENIED` o
            `GEOGRAPHY_UNAVAILABLE`); nunca se expone en la respuesta.
    """

    code = "DEPENDENCY_UNAVAILABLE"
    title = "Dependencia no disponible"
    default_message = "No fue posible validar el país contra Geography Service."

    def __init__(
        self,
        message: str | None = None,
        *,
        cause: str = GEOGRAPHY_UNAVAILABLE,
    ) -> None:
        super().__init__(message)
        self.cause = cause
