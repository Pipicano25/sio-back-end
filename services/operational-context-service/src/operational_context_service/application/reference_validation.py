"""Validaciones de referencias de la Fase B contra Party Identity y Keycloak.

Se llaman siempre sin transacción abierta (R-09 de la Fase A). En ningún
rechazo se guarda nada (RN-09). La indisponibilidad la lanzan los adaptadores
como `DependencyUnavailableError` y se expone como `503` con la extensión
`dependency` (C-13).
"""

from __future__ import annotations

from uuid import UUID

from operational_context_service.application.exceptions import (
    KeycloakUserDisabledError,
    KeycloakUserNotFoundError,
    PersonIdentityInactiveError,
    PersonIdentityNotFoundError,
    TechnicalAccountNotAllowedError,
)
from operational_context_service.application.location_validation import log_rejected_reference
from operational_context_service.application.ports import (
    AccountRef,
    IdentityAccountDirectory,
    PersonDirectory,
)
from operational_context_service.domain.status import ACTIVE


def validate_person(persons: PersonDirectory, person_identity_id: UUID) -> None:
    """La persona debe existir y estar `ACTIVE` (FR-017, FR-051, DS-15).

    Raises:
        PersonIdentityNotFoundError: `404` del proveedor.
        PersonIdentityInactiveError: `status = INACTIVE`.
        DependencyUnavailableError: Proveedor no disponible.
    """
    person = persons.get_person(person_identity_id)

    if person is None:
        error = PersonIdentityNotFoundError(field="person_identity_id")
        log_rejected_reference(error, person_identity_id)
        raise error

    if person.status != ACTIVE:
        error = PersonIdentityInactiveError(field="person_identity_id")
        log_rejected_reference(error, person_identity_id)
        raise error


def resolve_account(
    accounts: IdentityAccountDirectory,
    *,
    keycloak_user_id: str | None = None,
    username: str | None = None,
) -> AccountRef:
    """Resuelve la cuenta por `sub` o por nombre de usuario y la valida (FR-011, FR-019).

    Raises:
        KeycloakUserNotFoundError: No existe.
        KeycloakUserDisabledError: Deshabilitada.
        TechnicalAccountNotAllowedError: Es la cuenta de servicio de un cliente.
        DependencyUnavailableError: Keycloak no disponible.
    """
    field = "keycloak_user_id" if keycloak_user_id is not None else "username"

    if keycloak_user_id is not None:
        account = accounts.get_account(keycloak_user_id)
    else:
        account = accounts.find_account_by_username(username or "")

    if account is None:
        raise KeycloakUserNotFoundError(field=field)

    if account.is_service_account:
        raise TechnicalAccountNotAllowedError(field=field)

    if not account.enabled:
        raise KeycloakUserDisabledError(field=field)

    return account
