"""Excepciones de aplicación de Operational Context Service.

Son agnósticas del transporte (Principio XII): solo exponen `code`, mensaje y
campo. El estado HTTP lo asigna exclusivamente `api/errors.py`.
"""

from operational_context_service.domain.errors import (
    DomainValidationError,
    GeographyParentRequiredError,
    OperationalContextError,
)

# Causas internas: solo se registran en logs; se exponen como 503 (R-03).
ORGANIZATION_VALIDATION_DENIED = "ORGANIZATION_VALIDATION_DENIED"
PARTY_IDENTITY_UNAVAILABLE = "PARTY_IDENTITY_UNAVAILABLE"
GEOGRAPHY_VALIDATION_DENIED = "GEOGRAPHY_VALIDATION_DENIED"
GEOGRAPHY_UNAVAILABLE = "GEOGRAPHY_UNAVAILABLE"

__all__ = [
    "AdministrativeDivisionNotFoundError",
    "CityNotFoundError",
    "CompanyInactiveError",
    "CountryNotFoundError",
    "DependencyUnavailableError",
    "DomainValidationError",
    "DuplicateBranchCodeError",
    "DuplicateOrganizationIdentityError",
    "GeographyIncoherentError",
    "GeographyParentRequiredError",
    "ImmutableFieldError",
    "InvalidStatusTransitionError",
    "LocationInactiveError",
    "NotFoundError",
    "OperationalContextError",
    "OrganizationIdentityInactiveError",
    "OrganizationIdentityNotFoundError",
    "VersionConflictError",
]


class NotFoundError(OperationalContextError):
    """La empresa o sucursal de la ruta no existe."""

    code = "NOT_FOUND"
    title = "Recurso no encontrado"
    default_message = "El recurso solicitado no existe."


class ImmutableFieldError(OperationalContextError):
    """Se intentó cambiar un campo inmutable (p. ej. la empresa de una sucursal)."""

    code = "IMMUTABLE_FIELD"
    title = "Campo inmutable"
    default_message = "La solicitud intenta modificar un campo inmutable."


class CompanyInactiveError(OperationalContextError):
    """No se crean ni reactivan sucursales bajo una empresa inactiva (RN-09)."""

    code = "COMPANY_INACTIVE"
    title = "Empresa inactiva"
    default_message = (
        "La empresa está inactiva: no se pueden crear ni reactivar sus sucursales."
    )


class OrganizationIdentityNotFoundError(OperationalContextError):
    """Party Identity no conoce la organización indicada."""

    code = "ORGANIZATION_IDENTITY_NOT_FOUND"
    title = "Organización inexistente"
    default_message = "La organización indicada no existe en Party Identity Service."


class OrganizationIdentityInactiveError(OperationalContextError):
    """La organización existe pero está inactiva (DS-04)."""

    code = "ORGANIZATION_IDENTITY_INACTIVE"
    title = "Organización inactiva"
    default_message = (
        "La organización indicada está inactiva en Party Identity Service y no "
        "admite nuevas referencias."
    )


class CountryNotFoundError(OperationalContextError):
    """Geography no conoce el país indicado."""

    code = "COUNTRY_NOT_FOUND"
    title = "País inexistente"
    default_message = "El país indicado no existe en Geography Service."


class AdministrativeDivisionNotFoundError(OperationalContextError):
    """Geography no conoce la división indicada."""

    code = "ADMINISTRATIVE_DIVISION_NOT_FOUND"
    title = "División administrativa inexistente"
    default_message = "La división administrativa indicada no existe en Geography Service."


class CityNotFoundError(OperationalContextError):
    """Geography no conoce la ciudad indicada."""

    code = "CITY_NOT_FOUND"
    title = "Ciudad inexistente"
    default_message = "La ciudad indicada no existe en Geography Service."


class LocationInactiveError(OperationalContextError):
    """Un nivel geográfico existe pero está inactivo (DS-04)."""

    code = "LOCATION_INACTIVE"
    title = "Ubicación inactiva"
    default_message = (
        "La ubicación indicada está inactiva en Geography Service y no admite "
        "nuevas referencias."
    )


class GeographyIncoherentError(OperationalContextError):
    """País, división y ciudad no son coherentes entre sí (DS-05)."""

    code = "GEOGRAPHY_INCOHERENT"
    title = "Ubicación geográfica incoherente"
    default_message = "El país, la división administrativa y la ciudad no son coherentes."


class DuplicateOrganizationIdentityError(OperationalContextError):
    """La organización ya está vinculada a otra empresa (DS-03)."""

    code = "DUPLICATE_ORGANIZATION_IDENTITY"
    title = "Organización ya vinculada"
    default_message = "La organización indicada ya está vinculada a otra empresa."


class DuplicateBranchCodeError(OperationalContextError):
    """El código ya existe en la empresa (FR-021)."""

    code = "DUPLICATE_BRANCH_CODE"
    title = "Código de sucursal duplicado"
    default_message = "Ya existe una sucursal con ese código en la empresa."


class VersionConflictError(OperationalContextError):
    """La versión esperada está desactualizada."""

    code = "VERSION_CONFLICT"
    title = "Versión desactualizada"
    default_message = (
        "El recurso fue modificado por otra operación. Consulte la versión "
        "vigente y vuelva a intentarlo."
    )


class InvalidStatusTransitionError(OperationalContextError):
    """Inactivar lo ya inactivo o reactivar lo ya activo (DS-11)."""

    code = "INVALID_STATUS_TRANSITION"
    title = "Transición de estado inválida"
    default_message = "El recurso ya se encuentra en el estado solicitado."


class DependencyUnavailableError(OperationalContextError):
    """No fue posible validar contra Party Identity o Geography (FR-043).

    Attributes:
        provider: Servicio proveedor (`party-identity` o `geography`).
        cause: Causa interna, solo para logs (nunca se expone).
        operation: Operación del puerto que falló.
    """

    code = "DEPENDENCY_UNAVAILABLE"
    title = "Dependencia no disponible"
    default_message = (
        "No fue posible validar una referencia externa en este momento. "
        "Intente de nuevo más tarde; no se guardó ningún cambio."
    )

    def __init__(
        self,
        *,
        provider: str,
        cause: str,
        operation: str,
    ) -> None:
        super().__init__()
        self.provider = provider
        self.cause = cause
        self.operation = operation


# ---------------------------------------------------------------------------
# Fase B (feature 005): códigos por causa de dominio (FR-004). La
# indisponibilidad de Keycloak usa `DependencyUnavailableError` con
# `provider="keycloak"`; el `code` público sigue siendo DEPENDENCY_UNAVAILABLE y
# la dependencia se expone en la extensión `dependency` (C-13).
# ---------------------------------------------------------------------------

# Causas internas nuevas (solo logs).
KEYCLOAK_TOKEN_REJECTED = "KEYCLOAK_TOKEN_REJECTED"
KEYCLOAK_ADMIN_DENIED = "KEYCLOAK_ADMIN_DENIED"
KEYCLOAK_UNREACHABLE = "KEYCLOAK_UNREACHABLE"
KEYCLOAK_AMBIGUOUS_USERNAME = "KEYCLOAK_AMBIGUOUS_USERNAME"
PERSON_VALIDATION_DENIED = "PERSON_VALIDATION_DENIED"

from operational_context_service.domain.validity import InvalidValidityPeriodError  # noqa: E402

__all__ += [
    "BranchCompanyMismatchError",
    "BranchInactiveError",
    "DuplicateAdvisorAssignmentError",
    "DuplicateMembershipError",
    "DuplicateUserBranchError",
    "InvalidValidityPeriodError",
    "KeycloakUserDisabledError",
    "KeycloakUserNotFoundError",
    "MembershipInactiveError",
    "NoActivePrimaryAdvisorError",
    "PersonIdentityInactiveError",
    "PersonIdentityNotFoundError",
    "PrimaryAdvisorExistsError",
    "PrimaryAdvisorMismatchError",
    "TechnicalAccountNotAllowedError",
]


class KeycloakUserNotFoundError(OperationalContextError):
    """No existe en Keycloak una cuenta con ese `sub` o nombre de usuario (FR-011)."""

    code = "KEYCLOAK_USER_NOT_FOUND"
    title = "Cuenta inexistente"
    default_message = "No existe una cuenta de Keycloak con el identificador indicado."


class KeycloakUserDisabledError(OperationalContextError):
    """La cuenta existe pero está deshabilitada en Keycloak (FR-011)."""

    code = "KEYCLOAK_USER_DISABLED"
    title = "Cuenta deshabilitada"
    default_message = "La cuenta de Keycloak indicada está deshabilitada."


class TechnicalAccountNotAllowedError(OperationalContextError):
    """Las cuentas técnicas no se registran como usuarios operativos (FR-019)."""

    code = "TECHNICAL_ACCOUNT_NOT_ALLOWED"
    title = "Cuenta técnica no permitida"
    default_message = (
        "La cuenta indicada es la cuenta de servicio de un cliente técnico y no "
        "puede registrarse como usuario operativo."
    )


class PersonIdentityNotFoundError(OperationalContextError):
    """Party Identity no conoce la persona indicada (FR-017, FR-051)."""

    code = "PERSON_IDENTITY_NOT_FOUND"
    title = "Persona inexistente"
    default_message = "La persona indicada no existe en Party Identity Service."


class PersonIdentityInactiveError(OperationalContextError):
    """La persona existe pero está inactiva (FR-017, FR-051)."""

    code = "PERSON_IDENTITY_INACTIVE"
    title = "Persona inactiva"
    default_message = (
        "La persona indicada está inactiva en Party Identity Service y no admite "
        "nuevas referencias."
    )


class DuplicateMembershipError(OperationalContextError):
    """Ya existe una membresía `ACTIVE` de esa persona o cuenta en la empresa (FR-012)."""

    code = "DUPLICATE_MEMBERSHIP"
    title = "Membresía duplicada"
    default_message = (
        "Ya existe una membresía activa de esa persona o de esa cuenta en la empresa."
    )


class MembershipInactiveError(OperationalContextError):
    """La membresía está inactiva (FR-020)."""

    code = "MEMBERSHIP_INACTIVE"
    title = "Membresía inactiva"
    default_message = "La membresía del usuario operativo está inactiva."


class BranchInactiveError(OperationalContextError):
    """La sucursal está inactiva (FR-020)."""

    code = "BRANCH_INACTIVE"
    title = "Sucursal inactiva"
    default_message = "La sucursal está inactiva."


class BranchCompanyMismatchError(OperationalContextError):
    """La sucursal no pertenece a la empresa de la membresía (FR-020, RC-06)."""

    code = "BRANCH_COMPANY_MISMATCH"
    title = "Sucursal de otra empresa"
    default_message = "La sucursal no pertenece a la empresa del usuario operativo."


class DuplicateUserBranchError(OperationalContextError):
    """Ya existe la asignación usuario + sucursal (FR-021)."""

    code = "DUPLICATE_USER_BRANCH"
    title = "Asignación duplicada"
    default_message = (
        "El usuario ya tiene una asignación a esa sucursal; si está inactiva, "
        "reactívela."
    )


class PrimaryAdvisorExistsError(OperationalContextError):
    """Ya hay un asesor principal vigente (FR-052)."""

    code = "PRIMARY_ADVISOR_EXISTS"
    title = "Ya existe un asesor principal"
    default_message = (
        "La empresa ya tiene un asesor principal vigente; use el cambio de asesor principal."
    )


class DuplicateAdvisorAssignmentError(OperationalContextError):
    """La persona ya es asesora vigente de la empresa (FR-052)."""

    code = "DUPLICATE_ADVISOR_ASSIGNMENT"
    title = "Asesor ya vigente"
    default_message = "La persona ya es asesora vigente de la empresa."


class NoActivePrimaryAdvisorError(OperationalContextError):
    """Cambio de principal sin principal vigente (FR-053)."""

    code = "NO_ACTIVE_PRIMARY_ADVISOR"
    title = "Sin asesor principal vigente"
    default_message = "La empresa no tiene un asesor principal vigente que reemplazar."


class PrimaryAdvisorMismatchError(OperationalContextError):
    """La asignación indicada no es la principal vigente de la empresa (FR-053)."""

    code = "PRIMARY_ADVISOR_MISMATCH"
    title = "Asignación principal incorrecta"
    default_message = (
        "La asignación indicada no es la asignación principal vigente de la empresa."
    )
