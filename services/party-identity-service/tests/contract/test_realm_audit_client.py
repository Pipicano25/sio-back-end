"""Identidad técnica del servicio para emitir auditoría (feature 016; C-01/C-02; T005).

Lee la plantilla del realm: el cliente del servicio es confidencial con cuenta de servicio,
su token identifica al cliente (`client_id`, scope `service_account`) y lleva la audiencia
`sio-api`, y su cuenta de servicio conserva exactamente sus roles previos más
`perm:audit:audit-events:create`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REALM = (
    Path(__file__).resolve().parents[4]
    / "infrastructure" / "keycloak" / "realm-template" / "sio-realm.template.json"
)
CLIENT = "party-identity-service"
SERVICE_ACCOUNT_ID = "28bfb849-0520-423f-82b4-5bf16e7214de"
PREVIOUS_ROLES = {
    "sio-api:perm:geography:global_countries:read",
    "sio-api:perm:operational-context:application_users:read",
    "sio-api:perm:operational-context:platform:lookup",
}
AUDIT_ROLE = "perm:audit:audit-events:create"
SERVICE_ACCOUNT_SCOPES = {"acr", "basic", "email", "profile", "roles", "web-origins", "service_account"}


@pytest.fixture(scope="module")
def realm() -> dict:
    return json.loads(REALM.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def client(realm) -> dict:
    return next(item for item in realm["clients"] if item["clientId"] == CLIENT)


@pytest.fixture(scope="module")
def service_account(realm) -> dict:
    return next(user for user in realm["users"] if user.get("serviceAccountClientId") == CLIENT)


def test_client_is_a_confidential_service_account(client) -> None:
    assert client["publicClient"] is False
    assert client["serviceAccountsEnabled"] is True
    assert client["standardFlowEnabled"] is False
    assert client.get("directAccessGrantsEnabled") is False


def test_token_identifies_the_client_and_targets_the_api(client) -> None:
    assert SERVICE_ACCOUNT_SCOPES <= set(client.get("defaultClientScopes") or ())
    audiences = {
        mapper["config"].get("included.client.audience")
        for mapper in client.get("protocolMappers") or ()
        if mapper["protocolMapper"] == "oidc-audience-mapper"
    }
    assert "sio-api" in audiences


def test_service_account_keeps_previous_roles_and_adds_audit(service_account) -> None:
    assert service_account["id"] == SERVICE_ACCOUNT_ID
    roles = {
        f"{client_id}:{role}"
        for client_id, names in (service_account.get("clientRoles") or {}).items()
        for role in names
    }
    assert roles == PREVIOUS_ROLES | {f"sio-api:{AUDIT_ROLE}"}
