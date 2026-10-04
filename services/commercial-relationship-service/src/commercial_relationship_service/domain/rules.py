"""Reglas de dominio de las tres entidades (RN-03, RN-05, FR-020, FR-022)."""

from __future__ import annotations

from uuid import UUID

from commercial_relationship_service.domain.errors import (
    ContactPersonNotAllowedError,
    CustomerIdentityMismatchError,
    InventoryFlagsInvalidError,
)

PERSON = "PERSON"
ORGANIZATION = "ORGANIZATION"


def validate_inventory_flags(
    *,
    inventory_control_enabled: bool,
    lot_tracking_enabled: bool,
    expiration_tracking_enabled: bool,
) -> None:
    """Lotes exigen control de inventario; vencimiento exige lotes (RN-03).

    Raises:
        InventoryFlagsInvalidError: Con el campo que rompe la regla.
    """
    if lot_tracking_enabled and not inventory_control_enabled:
        raise InventoryFlagsInvalidError(
            "El control por lotes exige control de inventario.",
            field="lot_tracking_enabled",
        )

    if expiration_tracking_enabled and not lot_tracking_enabled:
        raise InventoryFlagsInvalidError(
            "El control de vencimiento exige control por lotes.",
            field="expiration_tracking_enabled",
        )


def validate_customer_identity(
    *,
    customer_kind: str,
    person_identity_id: UUID | None,
    organization_identity_id: UUID | None,
    preferred_contact_person_id: UUID | None,
) -> None:
    """Un cliente lleva exactamente la identidad de su tipo; contacto solo en organizaciones.

    Raises:
        CustomerIdentityMismatchError: Identidad ausente, de otro tipo o ambas.
        ContactPersonNotAllowedError: Contacto preferido en un cliente `PERSON`.
    """
    if customer_kind == PERSON:
        if person_identity_id is None or organization_identity_id is not None:
            raise CustomerIdentityMismatchError(field="person_identity_id")
        if preferred_contact_person_id is not None:
            raise ContactPersonNotAllowedError(field="preferred_contact_person_id")
        return

    if organization_identity_id is None or person_identity_id is not None:
        raise CustomerIdentityMismatchError(field="organization_identity_id")


def code_key(internal_code: str) -> str:
    """Clave de comparación de códigos internos: recortado y sin distinguir mayúsculas (DS-07)."""
    return internal_code.strip().lower()
