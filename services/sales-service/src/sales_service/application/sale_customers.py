"""Clientes de la venta: registro automático al crear y listado de quién puede comprar.

Al crear una venta el vendedor envía `company_customer_id` **o** la identidad global (`person_identity_id` u
`organization_identity_id`). Con la identidad:

1. Si ya es cliente de la empresa (en cualquier estado), se usa ese cliente; si está inactivo, la validación de la
   cabecera rechaza la venta con el nombre de la empresa en el mensaje.
2. Si no lo es, se registra en Commercial Relationship con el token del vendedor: código interno
   `{tipo}-{número}` de la identificación y nombre de Party Identity.

El listado combina una página de identidades `ACTIVE` de Party Identity con el estado de cada una como cliente de
la empresa (una sola llamada a Commercial Relationship por página).
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sales_service.application.exceptions import (
    COMMERCIAL_RELATIONSHIP,
    CustomerEnrollmentDeniedError,
    DependencyUnavailableError,
    ReferencesNotEligibleError,
    ValidationFailedError,
    field_error,
)
from sales_service.application.ports import (
    ORGANIZATION,
    PERSON,
    CompanyInfo,
    CustomerRegistry,
    CustomerRejection,
    Directories,
    IdentityInfo,
)

ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
NOT_CUSTOMER = "NOT_CUSTOMER"
INTERNAL_CODE_MAX = 60
DISPLAY_NAME_MAX = 200
COMPANY_FALLBACK = "la empresa"
IDENTITY_FIELDS = {PERSON: "person_identity_id", ORGANIZATION: "organization_identity_id"}


def company_name(directories: Directories, company: CompanyInfo) -> str:
    """Nombre de la empresa para los mensajes al vendedor (su identidad de organización)."""
    if company.organization_identity_id is None:
        return COMPANY_FALLBACK
    identity = directories.party.get_organization(company.organization_identity_id)
    return identity.name if identity is not None and identity.name else COMPANY_FALLBACK


def inactive_message(name: str) -> str:
    return f"El cliente no está habilitado para realizar compras en {name}."


def internal_code(identity: IdentityInfo) -> str:
    return f"{identity.identification_type}-{identity.identification_number}"[:INTERNAL_CODE_MAX]


def _registry(registry: CustomerRegistry | None) -> CustomerRegistry:
    if registry is None:
        raise DependencyUnavailableError(COMMERCIAL_RELATIONSHIP, operation="company_customers", cause="sin_registro")
    return registry


def customer_reference(
    company_customer_id: UUID | None, person_identity_id: UUID | None, organization_identity_id: UUID | None
) -> tuple[str | None, UUID | None]:
    """Exactamente una referencia del cliente: `(None, id)` del cliente o `(tipo, identidad)` (`422` si no)."""
    given = [value for value in (company_customer_id, person_identity_id, organization_identity_id) if value]
    if len(given) != 1:
        raise ValidationFailedError(
            [
                field_error(
                    "company_customer_id",
                    "CUSTOMER_REQUIRED" if not given else "CUSTOMER_REFERENCE_AMBIGUOUS",
                    "Indique uno solo de company_customer_id, person_identity_id u organization_identity_id.",
                )
            ]
        )
    if company_customer_id is not None:
        return None, company_customer_id
    if person_identity_id is not None:
        return PERSON, person_identity_id
    return ORGANIZATION, organization_identity_id


class CustomerEnrollment:
    def __init__(self, directories: Directories, registry: CustomerRegistry | None) -> None:
        self._dirs = directories
        self._registry = registry

    def ensure(self, company: CompanyInfo, customer_kind: str, identity_id: UUID) -> UUID:
        """`company_customer_id` de la identidad en la empresa; la registra si aún no es cliente."""
        registry = _registry(self._registry)
        field_name = IDENTITY_FIELDS[customer_kind]
        existing = registry.find(company.id, customer_kind, [identity_id]).get(identity_id)
        if existing is not None:
            return existing.id

        party = self._dirs.party
        identity = party.get_person(identity_id) if customer_kind == PERSON else party.get_organization(identity_id)
        if identity is None:
            missing = "PERSON_IDENTITY_NOT_FOUND" if customer_kind == PERSON else "ORGANIZATION_IDENTITY_NOT_FOUND"
            raise ValidationFailedError([field_error(field_name, missing, "La identidad no existe en Party Identity.")])
        if identity.status is not None and identity.status != ACTIVE:
            raise ReferencesNotEligibleError(
                [field_error(field_name, "IDENTITY_INACTIVE", "La identidad no está activa en Party Identity.")]
            )
        if not identity.identification_type or not identity.identification_number:
            raise ReferencesNotEligibleError(
                [
                    field_error(
                        field_name,
                        "CUSTOMER_IDENTIFICATION_MISSING",
                        "La identidad no tiene el tipo y el número de identificación obligatorios.",
                    )
                ]
            )

        code = internal_code(identity)
        name = (identity.name or code)[:DISPLAY_NAME_MAX]
        try:
            return registry.create(company.id, customer_kind, identity_id, code, name).id
        except CustomerRejection as rejection:
            return self._rejected(rejection, company, customer_kind, identity_id, field_name, code)

    def _rejected(
        self,
        rejection: CustomerRejection,
        company: CompanyInfo,
        customer_kind: str,
        identity_id: UUID,
        field_name: str,
        code: str,
    ) -> UUID:
        if rejection.status == 403:
            raise CustomerEnrollmentDeniedError() from None
        if rejection.code == "DUPLICATE_CUSTOMER":
            # Otro vendedor lo registró entre la búsqueda y el alta: se usa ese cliente.
            existing = _registry(self._registry).find(company.id, customer_kind, [identity_id]).get(identity_id)
            if existing is not None:
                return existing.id
        if rejection.code == "DUPLICATE_INTERNAL_CODE":
            raise ReferencesNotEligibleError(
                [
                    field_error(
                        field_name,
                        "CUSTOMER_CODE_TAKEN",
                        f"La empresa ya tiene otro cliente con el código {code}. Registre este cliente manualmente "
                        "con otro código.",
                    )
                ]
            ) from None
        if rejection.status in (409, 422):
            raise ReferencesNotEligibleError(
                [
                    field_error(
                        field_name,
                        rejection.code or "CUSTOMER_NOT_REGISTERED",
                        rejection.message or "Commercial Relationship no permitió registrar el cliente.",
                    )
                ]
            ) from None
        raise DependencyUnavailableError(
            COMMERCIAL_RELATIONSHIP, operation="company_customer_create", cause=f"estado={rejection.status}"
        ) from None


@dataclass(frozen=True, slots=True)
class SaleCustomer:
    customer_kind: str
    identity_id: UUID
    name: str | None
    identification_type: str | None
    identification_number: str | None
    company_customer_id: UUID | None
    customer_status: str
    can_buy: bool
    message: str | None


@dataclass(frozen=True, slots=True)
class SaleCustomerPage:
    items: list[SaleCustomer]
    total_records: int


class SaleCustomerService:
    def __init__(self, directories: Directories, registry: CustomerRegistry | None) -> None:
        self._dirs = directories
        self._registry = registry

    def list(
        self, company: CompanyInfo, customer_kind: str, search: str | None, page: int, page_size: int
    ) -> SaleCustomerPage:
        identities = self._dirs.party.search(customer_kind, search, page, page_size)
        customers = _registry(self._registry).find(company.id, customer_kind, [item.id for item in identities.items])
        name = company_name(self._dirs, company)

        items = []
        for identity in identities.items:
            customer = customers.get(identity.id)
            status = NOT_CUSTOMER if customer is None else customer.status
            can_buy, message = True, None
            if customer_kind == ORGANIZATION and identity.id == company.organization_identity_id:
                can_buy, message = False, "Es la propia empresa: no puede ser su cliente."
            elif status not in (ACTIVE, NOT_CUSTOMER):
                can_buy, message = False, inactive_message(name)
            elif not identity.identification_type or not identity.identification_number:
                can_buy, message = False, "La identidad no tiene el tipo y el número de identificación obligatorios."
            elif status == NOT_CUSTOMER:
                message = f"Aún no es cliente de {name}; se registrará automáticamente al crear la venta."
            items.append(
                SaleCustomer(
                    customer_kind=customer_kind,
                    identity_id=identity.id,
                    name=customer.display_name if customer is not None else identity.name,
                    identification_type=identity.identification_type,
                    identification_number=identity.identification_number,
                    company_customer_id=customer.id if customer is not None else None,
                    customer_status=status,
                    can_buy=can_buy,
                    message=message,
                )
            )
        return SaleCustomerPage(items=items, total_records=identities.total_records)
