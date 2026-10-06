"""Identidad técnica y capacidad `platform:lookup` (R-02, R-08, RC-01; T008)."""

from __future__ import annotations

import pytest

from inventory_service.api.identity import has_platform_lookup, service_account_client_id


@pytest.mark.parametrize(
    ("claims", "expected"),
    [
        ({"preferred_username": "admin.test"}, None),
        ({"preferred_username": "service-account-inventory-test-operator"}, None),
        ({"client_id": "sio-web", "preferred_username": "admin.test"}, None),
        ({"client_id": "inventory", "preferred_username": "service-account-inventory-test-operator"}, None),
        ({"client_id": "inventory-test-operator", "preferred_username": "service-account-inventory-test-operatorX"}, None),
        ({"client_id": "", "preferred_username": "service-account-"}, None),
        (
            {"client_id": "inventory-test-operator", "preferred_username": "service-account-inventory-test-operator"},
            "inventory-test-operator",
        ),
    ],
)
def test_service_account_correlation(claims, expected) -> None:
    assert service_account_client_id(claims) == expected


def test_platform_lookup_requires_the_permission() -> None:
    assert has_platform_lookup({"perm:inventory:platform:lookup"})
    assert has_platform_lookup({"perm:inventory:all:all"})
    assert not has_platform_lookup({"perm:inventory:balances:read"})
    assert not has_platform_lookup(set())
