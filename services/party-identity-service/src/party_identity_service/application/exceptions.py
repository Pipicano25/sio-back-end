"""Excepciones de aplicación de Party Identity Service.

Son agnósticas del transporte (Principio XII): solo exponen un `code` estable,
un mensaje y, cuando aplica, contexto. El estado HTTP lo asigna exclusivamente
`api/errors.py`. Los mensajes nunca incluyen números de identificación ni
fechas de nacimiento completos (DS-09).
"""

from typing import Any, Literal

COUNTRY_VALIDATION_DENIED = "COUNTRY_VALIDATION_DENIED"
GEOGRAPHY_UNAVAILABLE = "GEOGRAPHY_UNAVAILABLE"
OPERATIONAL_CONTEXT_VALIDATION_DENIED = "OPERATIONAL_CONTEXT_VALIDATION_DENIED"
OPERATIONAL_CONTEXT_UNAVAILABLE = "OPERATIONAL_CONTEXT_UNAVAILABLE"
KEYCLOAK_TOKEN_UNAVAILABLE = "KEYCLOAK_TOKEN_UNAVAILABLE"

Dependency = Literal["geography", "operational-context", "keycloak"]


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
    """No fue posible validar contra una dependencia externa (DS-14).

    Todas las fallas de dependencia comparten el código público
    `DEPENDENCY_UNAVAILABLE`; la extensión `dependency` indica cuál falló
    (cambio aditivo respecto de la Fase A, regla 4.3).

    Attributes:
        dependency: `geography`, `operational-context` o `keycloak`; se expone
            como extensión del Problem Details.
        cause: Causa interna solo para logs (p. ej. `COUNTRY_VALIDATION_DENIED`);
            nunca se expone en la respuesta.
    """

    code = "DEPENDENCY_UNAVAILABLE"
    title = "Dependencia no disponible"
    default_message = "No fue posible validar contra un servicio externo."

    _MESSAGES: dict[str, str] = {
        "geography": "No fue posible validar el país contra Geography Service.",
        "operational-context": "No fue posible validar la membresía en Operational Context.",
        "keycloak": "No fue posible obtener la identidad técnica del servicio.",
    }

    def __init__(
        self,
        message: str | None = None,
        *,
        dependency: Dependency,
        cause: str,
    ) -> None:
        super().__init__(
            message or self._MESSAGES.get(dependency),
            context={"dependency": dependency},
        )
        self.dependency = dependency
        self.cause = cause


# --------------------------------------------------------------------------
# Fase B: perfiles, contactos, sectores y representantes (contracts/errors.md)
# --------------------------------------------------------------------------


class ContactProfileNotFoundError(PartyIdentityError):
    """No hay perfil vigente (consulta) o nunca existió perfil (cierre)."""

    code = "CONTACT_PROFILE_NOT_FOUND"
    title = "Perfil de contacto inexistente"
    default_message = "La identidad no tiene un perfil de contacto vigente."


class ContactProfileAlreadyClosedError(PartyIdentityError):
    """No hay perfil vigente pero sí historia cerrada (cierre repetido)."""

    code = "CONTACT_PROFILE_ALREADY_CLOSED"
    title = "Perfil de contacto ya cerrado"
    default_message = "El perfil de contacto ya está cerrado; no hay versión vigente."


class PersonIdentityInactiveError(PartyIdentityError):
    """La persona está `INACTIVE` y no admite relaciones nuevas."""

    code = "PERSON_IDENTITY_INACTIVE"
    title = "Persona inactiva"
    default_message = "La persona está inactiva y no admite nuevas asignaciones."


class OrganizationIdentityInactiveError(PartyIdentityError):
    """La organización está `INACTIVE` y no admite relaciones nuevas."""

    code = "ORGANIZATION_IDENTITY_INACTIVE"
    title = "Organización inactiva"
    default_message = "La organización está inactiva y no admite nuevas asignaciones."


class PersonIdentityNotFoundError(PartyIdentityError):
    """La persona indicada en el cuerpo no existe."""

    code = "PERSON_IDENTITY_NOT_FOUND"
    title = "Persona inexistente"
    default_message = "La persona indicada no existe."


class AdministrativeDivisionNotFoundError(PartyIdentityError):
    """La división administrativa no existe en Geography Service."""

    code = "ADMINISTRATIVE_DIVISION_NOT_FOUND"
    title = "División administrativa inexistente"
    default_message = "La división administrativa indicada no existe en Geography Service."


class CityNotFoundError(PartyIdentityError):
    """La ciudad no existe en Geography Service."""

    code = "CITY_NOT_FOUND"
    title = "Ciudad inexistente"
    default_message = "La ciudad indicada no existe en Geography Service."


class _FieldContextMixin:
    """Añade la extensión `field` a un error de geografía."""

    def __init__(self, message: str | None = None, *, field: str) -> None:
        PartyIdentityError.__init__(self, message, context={"field": field})
        self.field = field


class LocationInactiveError(_FieldContextMixin, PartyIdentityError):
    """Un nivel geográfico está `INACTIVE`."""

    code = "LOCATION_INACTIVE"
    title = "Ubicación inactiva"
    default_message = "La ubicación indicada está inactiva en Geography Service."


class GeographyIncoherentError(_FieldContextMixin, PartyIdentityError):
    """La división o la ciudad no corresponden a los niveles superiores."""

    code = "GEOGRAPHY_INCOHERENT"
    title = "Geografía incoherente"
    default_message = "La ubicación no es coherente con los niveles superiores indicados."


class GeographyParentRequiredError(_FieldContextMixin, PartyIdentityError):
    """Se informó un nivel inferior sin el país."""

    code = "GEOGRAPHY_PARENT_REQUIRED"
    title = "Falta el nivel geográfico superior"
    default_message = "La división o la ciudad exigen informar el país."


class CompanyNotFoundError(PartyIdentityError):
    """La empresa de confirmación no existe en Operational Context."""

    code = "COMPANY_NOT_FOUND"
    title = "Empresa inexistente"
    default_message = "La empresa indicada no existe en Operational Context."


class CompanyInactiveError(PartyIdentityError):
    """La empresa de confirmación está inactiva."""

    code = "COMPANY_INACTIVE"
    title = "Empresa inactiva"
    default_message = "La empresa indicada está inactiva."


class ConfirmationMembershipInvalidError(PartyIdentityError):
    """El usuario no tiene membresía `ACTIVE` en la empresa de confirmación."""

    code = "CONFIRMATION_MEMBERSHIP_INVALID"
    title = "Membresía de confirmación inválida"
    default_message = (
        "El usuario no tiene una membresía activa en la empresa desde la que "
        "confirma el perfil."
    )

    def __init__(self, message: str | None = None, *, reason: str) -> None:
        super().__init__(message, context={"reason": reason})
        self.reason = reason


class InvalidPrimaryContactError(PartyIdentityError):
    """`set-primary` sobre un contacto `INACTIVE`."""

    code = "INVALID_PRIMARY_CONTACT"
    title = "Contacto principal inválido"
    default_message = "Solo un contacto activo puede marcarse como principal."


class PrimaryContactConflictError(PartyIdentityError):
    """Ya existe un contacto principal vigente."""

    code = "PRIMARY_CONTACT_CONFLICT"
    title = "Contacto principal existente"
    default_message = (
        "La organización ya tiene un contacto principal; use set-primary para "
        "sustituirlo."
    )


class DuplicateActiveContactPersonError(PartyIdentityError):
    """La persona ya es contacto vigente de la organización."""

    code = "DUPLICATE_ACTIVE_CONTACT_PERSON"
    title = "Contacto duplicado"
    default_message = "La persona ya es contacto vigente de la organización."


class DuplicateSectorCodeError(PartyIdentityError):
    """El código ya existe en el sistema de clasificación."""

    code = "DUPLICATE_SECTOR_CODE"
    title = "Código de sector duplicado"
    default_message = "Ya existe un sector con ese código en el sistema de clasificación."


class InvalidSectorHierarchyError(PartyIdentityError):
    """Padre inexistente, inactivo, de otro sistema o ciclo."""

    code = "INVALID_SECTOR_HIERARCHY"
    title = "Jerarquía de sectores inválida"
    default_message = (
        "El sector superior debe existir, estar activo, pertenecer al mismo "
        "sistema de clasificación y no formar ciclos."
    )


class SectorHasActiveChildrenError(PartyIdentityError):
    """El sector tiene hijos `ACTIVE`."""

    code = "SECTOR_HAS_ACTIVE_CHILDREN"
    title = "Sector con hijos activos"
    default_message = "No se puede inactivar un sector con sectores hijos activos."


class SectorInactiveError(PartyIdentityError):
    """El sector está `INACTIVE` y no admite asignaciones nuevas."""

    code = "SECTOR_INACTIVE"
    title = "Sector inactivo"
    default_message = "El sector está inactivo y no admite nuevas asignaciones."


class DuplicateActiveSectorAssignmentError(PartyIdentityError):
    """La organización ya tiene ese sector vigente."""

    code = "DUPLICATE_ACTIVE_SECTOR_ASSIGNMENT"
    title = "Sector ya asignado"
    default_message = "La organización ya tiene ese sector vigente."


class PrimarySectorConflictError(PartyIdentityError):
    """Ya existe un sector principal vigente."""

    code = "PRIMARY_SECTOR_CONFLICT"
    title = "Sector principal existente"
    default_message = (
        "La organización ya tiene un sector principal; use set-primary para "
        "sustituirlo."
    )


class InvalidPrimarySectorError(PartyIdentityError):
    """`set-primary` sobre una asignación cerrada."""

    code = "INVALID_PRIMARY_SECTOR"
    title = "Sector principal inválido"
    default_message = "Solo una asignación vigente puede marcarse como principal."


class PrimaryRepresentativeConflictError(PartyIdentityError):
    """Ya existe un representante `PRIMARY` vigente."""

    code = "PRIMARY_REPRESENTATIVE_CONFLICT"
    title = "Representante principal existente"
    default_message = (
        "La organización ya tiene un representante legal PRIMARY vigente; use "
        "set-primary para sustituirlo."
    )


class DuplicateActiveRepresentativeError(PartyIdentityError):
    """La persona ya tiene una relación vigente con la organización."""

    code = "DUPLICATE_ACTIVE_REPRESENTATIVE"
    title = "Representante duplicado"
    default_message = (
        "La persona ya tiene una relación de representación vigente con la "
        "organización."
    )


class DomainValidationError(PartyIdentityError):
    """Validación de entrada detectada en la capa de aplicación.

    Usa el código público existente `VALIDATION_ERROR` con el mismo detalle por
    campo (`errors[]`) que la validación de esquemas (D13); no es un código nuevo.
    """

    code = "VALIDATION_ERROR"
    title = "Solicitud inválida"
    default_message = "La solicitud contiene datos inválidos."

    def __init__(self, field: str, message: str) -> None:
        super().__init__(
            None,
            context={"errors": [{"field": field, "message": message, "code": "VALIDATION_ERROR"}]},
        )
        self.field = field
