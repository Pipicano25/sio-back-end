"""Excepciones de aplicación de Commercial Relationship Service (`contracts/errors.md`).

Son agnósticas del transporte (Principio XII): solo exponen `code`, mensaje y
campo. El estado HTTP lo asigna exclusivamente `api/errors.py`.
"""

from commercial_relationship_service.domain.errors import (
    CommercialRelationshipError,
    ContactPersonNotAllowedError,
    CurrencyNotSupportedError,
    CustomerIdentityMismatchError,
    InventoryFlagsInvalidError,
    InvalidStatusTransitionError,
    PriceScaleNotAllowedError,
)

# Proveedores (extensión `dependency` del 503; catálogo cerrado).
OPERATIONAL_CONTEXT = "operational-context"
PRODUCT_CATALOG = "product-catalog"
PARTY_IDENTITY = "party-identity"

# Causas internas: solo se registran en logs (contracts/errors.md).
OPERATIONAL_CONTEXT_UNREACHABLE = "OPERATIONAL_CONTEXT_UNREACHABLE"
OPERATIONAL_ACCESS_FORBIDDEN = "OPERATIONAL_ACCESS_FORBIDDEN"
KEYCLOAK_TOKEN_REJECTED = "KEYCLOAK_TOKEN_REJECTED"
PRODUCT_CATALOG_ACCESS_DENIED = "PRODUCT_CATALOG_ACCESS_DENIED"
PRODUCT_CATALOG_UNREACHABLE = "PRODUCT_CATALOG_UNREACHABLE"
PARTY_IDENTITY_UNREACHABLE = "PARTY_IDENTITY_UNREACHABLE"
PARTY_IDENTITY_FORBIDDEN = "PARTY_IDENTITY_FORBIDDEN"

__all__ = [
    "CommercialRelationshipError",
    "CompanyInactiveError",
    "ContactPersonInvalidError",
    "ContactPersonNotAllowedError",
    "CurrencyNotSupportedError",
    "CustomerIdentityMismatchError",
    "DependencyUnavailableError",
    "DuplicateAdoptionError",
    "DuplicateCustomerError",
    "DuplicateInternalCodeError",
    "DuplicateSupplierError",
    "GlobalProductInactiveError",
    "GlobalProductNotEligibleError",
    "GlobalProductNotFoundError",
    "BatchLimitExceededError",
    "InventoryFlagsInvalidError",
    "InvalidStatusTransitionError",
    "NotFoundError",
    "OperationalAccessDeniedError",
    "OrganizationIdentityInactiveError",
    "OrganizationIdentityNotFoundError",
    "PartyIdentityAccessDeniedError",
    "PersonIdentityInactiveError",
    "PersonIdentityNotFoundError",
    "PriceScaleNotAllowedError",
    "SelfRelationshipNotAllowedError",
    "VersionConflictError",
]


class NotFoundError(CommercialRelationshipError):
    """Recurso inexistente o fuera del alcance del usuario (FR-041; cuerpo idéntico)."""

    code = "NOT_FOUND"
    title = "Recurso no encontrado"
    default_message = "El recurso solicitado no existe."


class OperationalAccessDeniedError(CommercialRelationshipError):
    """Operational Context respondió `403` al usuario (FR-052, FR-028)."""

    code = "OPERATIONAL_ACCESS_DENIED"
    title = "Acceso operativo denegado"
    default_message = (
        "Su usuario no tiene permiso en Operational Context para consultar el acceso "
        "operativo o la empresa. No se guardó ningún cambio."
    )


class PartyIdentityAccessDeniedError(CommercialRelationshipError):
    """Party Identity respondió `403` al usuario (FR-054)."""

    code = "PARTY_IDENTITY_ACCESS_DENIED"
    title = "Consulta de identidad denegada"
    default_message = (
        "Su usuario no tiene permiso en Party Identity para consultar la identidad o la "
        "persona de contacto indicada. No se guardó ningún cambio."
    )


class CompanyInactiveError(CommercialRelationshipError):
    """Escritura distinta de inactivar bajo una empresa inactiva (FR-042, RN-11)."""

    code = "COMPANY_INACTIVE"
    title = "Empresa inactiva"
    default_message = "La empresa está inactiva: solo se permite consultar e inactivar."


class GlobalProductNotFoundError(CommercialRelationshipError):
    """Product Catalog no encontró el producto global (FR-011, FR-016)."""

    code = "GLOBAL_PRODUCT_NOT_FOUND"
    title = "Producto global inexistente"
    default_message = "El producto global indicado no existe en Product Catalog."


class GlobalProductInactiveError(CommercialRelationshipError):
    """El producto global está inactivo al adoptar o reactivar (FR-011, FR-016)."""

    code = "GLOBAL_PRODUCT_INACTIVE"
    title = "Producto global inactivo"
    default_message = "El producto global indicado está inactivo en Product Catalog."


class GlobalProductNotEligibleError(CommercialRelationshipError):
    """El producto global no es elegible para adopción: está incompleto (FR-011)."""

    code = "GLOBAL_PRODUCT_NOT_ELIGIBLE"
    title = "Producto global no elegible"
    default_message = "El producto global no está completo y no se puede adoptar."


class PersonIdentityNotFoundError(CommercialRelationshipError):
    """Party Identity no conoce la persona (FR-021)."""

    code = "PERSON_IDENTITY_NOT_FOUND"
    title = "Persona inexistente"
    default_message = "La persona indicada no existe en Party Identity."


class PersonIdentityInactiveError(CommercialRelationshipError):
    """La persona existe pero está inactiva (FR-021, FR-025)."""

    code = "PERSON_IDENTITY_INACTIVE"
    title = "Persona inactiva"
    default_message = "La persona indicada está inactiva en Party Identity."


class OrganizationIdentityNotFoundError(CommercialRelationshipError):
    """Party Identity no conoce la organización (FR-021, FR-031)."""

    code = "ORGANIZATION_IDENTITY_NOT_FOUND"
    title = "Organización inexistente"
    default_message = "La organización indicada no existe en Party Identity."


class OrganizationIdentityInactiveError(CommercialRelationshipError):
    """La organización existe pero está inactiva (FR-021, FR-033)."""

    code = "ORGANIZATION_IDENTITY_INACTIVE"
    title = "Organización inactiva"
    default_message = "La organización indicada está inactiva en Party Identity."


class ContactPersonInvalidError(CommercialRelationshipError):
    """Contacto inexistente, inactivo o de otra organización (FR-022, FR-031)."""

    code = "CONTACT_PERSON_INVALID"
    title = "Persona de contacto inválida"
    default_message = (
        "La persona de contacto no existe, está inactiva o no pertenece a la organización."
    )


class SelfRelationshipNotAllowedError(CommercialRelationshipError):
    """La organización es la de la propia empresa (FR-028, FR-031)."""

    code = "SELF_RELATIONSHIP_NOT_ALLOWED"
    title = "Relación con la propia empresa"
    default_message = "Una empresa no puede ser cliente ni proveedor de sí misma."


class DuplicateAdoptionError(CommercialRelationshipError):
    """El producto ya está adoptado por la empresa, en cualquier estado (FR-012)."""

    code = "DUPLICATE_ADOPTION"
    title = "Producto ya adoptado"
    default_message = (
        "La empresa ya adoptó este producto global; si está inactivo, reactívelo."
    )


class DuplicateCustomerError(CommercialRelationshipError):
    """La identidad ya es cliente de la empresa, en cualquier estado (FR-023)."""

    code = "DUPLICATE_CUSTOMER"
    title = "Cliente duplicado"
    default_message = "La identidad ya es cliente de la empresa; si está inactivo, reactívelo."


class DuplicateSupplierError(CommercialRelationshipError):
    """La organización ya es proveedor de la empresa, en cualquier estado (FR-032)."""

    code = "DUPLICATE_SUPPLIER"
    title = "Proveedor duplicado"
    default_message = (
        "La organización ya es proveedor de la empresa; si está inactivo, reactívelo."
    )


class DuplicateInternalCodeError(CommercialRelationshipError):
    """Código interno ya usado en la empresa para esa entidad (FR-013, FR-023, FR-032)."""

    code = "DUPLICATE_INTERNAL_CODE"
    title = "Código interno duplicado"
    default_message = "Ya existe un registro con ese código interno en la empresa."


class VersionConflictError(CommercialRelationshipError):
    """La versión esperada está desactualizada (FR-072)."""

    code = "VERSION_CONFLICT"
    title = "Versión desactualizada"
    default_message = (
        "El recurso fue modificado por otra operación. Consulte la versión vigente y "
        "vuelva a intentarlo."
    )


class BatchLimitExceededError(CommercialRelationshipError):
    """Más de 100 UUID en la consulta por lotes (FR-062)."""

    code = "BATCH_LIMIT_EXCEEDED"
    title = "Lote demasiado grande"
    default_message = "La consulta por lotes admite como máximo 100 identificadores."


class DependencyUnavailableError(CommercialRelationshipError):
    """No fue posible validar contra un proveedor (FR-043, FR-055).

    Attributes:
        provider: `operational-context`, `product-catalog` o `party-identity`.
        cause: Causa interna, solo para logs (nunca se expone).
        operation: Operación del puerto que falló.
    """

    code = "DEPENDENCY_UNAVAILABLE"
    title = "Dependencia no disponible"
    default_message = (
        "No fue posible validar una referencia externa en este momento. Intente de nuevo "
        "más tarde; no se guardó ningún cambio."
    )

    def __init__(self, *, provider: str, cause: str, operation: str) -> None:
        super().__init__()
        self.provider = provider
        self.cause = cause
        self.operation = operation
