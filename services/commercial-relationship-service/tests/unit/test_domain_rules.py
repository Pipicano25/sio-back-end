"""Reglas de dominio: banderas, tipo de cliente, transiciones y códigos (RC-07, RC-08)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from commercial_relationship_service.domain.errors import (
    ContactPersonNotAllowedError,
    CustomerIdentityMismatchError,
    InventoryFlagsInvalidError,
    InvalidStatusTransitionError,
)
from commercial_relationship_service.domain.rules import (
    code_key,
    validate_customer_identity,
    validate_inventory_flags,
)
from commercial_relationship_service.domain.status import (
    ACTIVE,
    BLOCK,
    BLOCKED,
    DEACTIVATE,
    INACTIVE,
    REACTIVATE,
    UNBLOCK,
    next_status,
)


def test_inventory_flags():
    validate_inventory_flags(
        inventory_control_enabled=True, lot_tracking_enabled=True, expiration_tracking_enabled=True
    )

    with pytest.raises(InventoryFlagsInvalidError) as error:
        validate_inventory_flags(
            inventory_control_enabled=False, lot_tracking_enabled=True, expiration_tracking_enabled=False
        )
    assert error.value.field == "lot_tracking_enabled"

    with pytest.raises(InventoryFlagsInvalidError) as error:
        validate_inventory_flags(
            inventory_control_enabled=True, lot_tracking_enabled=False, expiration_tracking_enabled=True
        )
    assert error.value.field == "expiration_tracking_enabled"


@pytest.mark.parametrize(
    ("kind", "person", "organization"),
    [
        ("PERSON", None, None),
        ("PERSON", uuid4(), uuid4()),
        ("ORGANIZATION", None, None),
        ("ORGANIZATION", uuid4(), uuid4()),
        ("PERSON", None, uuid4()),
        ("ORGANIZATION", uuid4(), None),
    ],
)
def test_customer_identity_mismatch(kind, person, organization):
    with pytest.raises(CustomerIdentityMismatchError):
        validate_customer_identity(
            customer_kind=kind,
            person_identity_id=person,
            organization_identity_id=organization,
            preferred_contact_person_id=None,
        )


def test_contact_only_for_organizations():
    with pytest.raises(ContactPersonNotAllowedError):
        validate_customer_identity(
            customer_kind="PERSON",
            person_identity_id=uuid4(),
            organization_identity_id=None,
            preferred_contact_person_id=uuid4(),
        )

    validate_customer_identity(
        customer_kind="ORGANIZATION",
        person_identity_id=None,
        organization_identity_id=uuid4(),
        preferred_contact_person_id=uuid4(),
    )


SIMPLE = [
    (ACTIVE, DEACTIVATE, INACTIVE),
    (INACTIVE, REACTIVATE, ACTIVE),
]
SIMPLE_INVALID = [(ACTIVE, REACTIVATE), (INACTIVE, DEACTIVATE), (ACTIVE, BLOCK), (ACTIVE, UNBLOCK)]

SUPPLIER = [
    (ACTIVE, DEACTIVATE, INACTIVE),
    (INACTIVE, REACTIVATE, ACTIVE),
    (ACTIVE, BLOCK, BLOCKED),
    (INACTIVE, BLOCK, BLOCKED),
    (BLOCKED, UNBLOCK, ACTIVE),
]
SUPPLIER_INVALID = [
    (BLOCKED, DEACTIVATE),
    (BLOCKED, REACTIVATE),
    (BLOCKED, BLOCK),
    (ACTIVE, UNBLOCK),
    (INACTIVE, UNBLOCK),
    (ACTIVE, REACTIVATE),
    (INACTIVE, DEACTIVATE),
]


@pytest.mark.parametrize(("current", "action", "target"), SIMPLE)
def test_simple_transitions(current, action, target):
    assert next_status(current, action) == target


@pytest.mark.parametrize(("current", "action"), SIMPLE_INVALID)
def test_simple_invalid_transitions(current, action):
    with pytest.raises(InvalidStatusTransitionError):
        next_status(current, action)


@pytest.mark.parametrize(("current", "action", "target"), SUPPLIER)
def test_supplier_transitions(current, action, target):
    assert next_status(current, action, supplier=True) == target


@pytest.mark.parametrize(("current", "action"), SUPPLIER_INVALID)
def test_supplier_invalid_transitions(current, action):
    with pytest.raises(InvalidStatusTransitionError):
        next_status(current, action, supplier=True)


def test_code_key_trims_and_ignores_case():
    assert code_key("  ABC-1 ") == code_key("abc-1") == "abc-1"
