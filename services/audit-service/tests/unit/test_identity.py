"""Correlación de claims de cuenta de servicio (RC-01, RC-03; T013)."""

from __future__ import annotations

import pytest

from audit_service.api.identity import service_account_client_id


def test_service_account_is_recognized() -> None:
    claims = {"client_id": "inventory-service", "preferred_username": "service-account-inventory-service"}
    assert service_account_client_id(claims) == "inventory-service"


@pytest.mark.parametrize(
    "claims",
    [
        {"preferred_username": "admin.test"},
        {"preferred_username": "service-account-inventory-service"},
        {"client_id": "inventory-service"},
        {"client_id": "inventory-service", "preferred_username": "admin.test"},
        {"client_id": "inventory-service", "preferred_username": "service-account-other"},
        {"client_id": "inventory", "preferred_username": "service-account-inventory-service"},
        {"client_id": "", "preferred_username": "service-account-"},
        {"client_id": 5, "preferred_username": "service-account-5"},
        {"azp": "inventory-service", "preferred_username": "service-account-inventory-service"},
    ],
)
def test_other_tokens_are_not_service_accounts(claims) -> None:
    assert service_account_client_id(claims) is None
