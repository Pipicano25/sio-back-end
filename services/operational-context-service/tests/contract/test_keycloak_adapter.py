"""Adaptador de solo lectura de la Admin API de Keycloak (R-06, R-07, RC-05).

Contrato: `specs/005-operational-context-users/contracts/keycloak-dependency.md`.
"""

import logging

import httpx
import pytest

from operational_context_service.application.exceptions import DependencyUnavailableError
from operational_context_service.infrastructure.keycloak_account_directory import (
    KeycloakAccountDirectory,
)
from operational_context_service.infrastructure.keycloak_token_client import KeycloakTokenClient
from operational_context_service.observability import SERVICE_LOGGER, configure_logging

SECRET = "secreto-super-confidencial"
ADMIN = "http://keycloak.test/admin/realms/sio"
TOKEN_URL = "http://keycloak.test/realms/sio/protocol/openid-connect/token"
SUB = "8f2c1d3e-0000-4000-8000-000000000001"


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class KeycloakStub:
    """Simula token y Admin API; registra las llamadas."""

    def __init__(self):
        self.token_requests = 0
        self.calls = []
        self.token_status = 200
        self.routes = {}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if str(request.url) == TOKEN_URL:
            self.token_requests += 1
            body = dict(httpx.QueryParams(request.content.decode()))
            assert body["grant_type"] == "client_credentials"
            assert body["client_id"] == "operational-context-service"
            if self.token_status != 200:
                return httpx.Response(self.token_status)
            return httpx.Response(
                200,
                json={"access_token": f"tok-{self.token_requests}", "expires_in": 300},
            )

        self.calls.append(request)
        handler = self.routes.get(request.url.path)
        if handler is None:
            return httpx.Response(404)
        return handler(request) if callable(handler) else handler


@pytest.fixture(autouse=True)
def logging_configured():
    configure_logging()


@pytest.fixture
def stub():
    return KeycloakStub()


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def directory(stub, clock):
    transport = httpx.MockTransport(stub)
    token_client = KeycloakTokenClient(
        base_url="http://keycloak.test/",
        realm="sio",
        client_id="operational-context-service",
        client_secret=SECRET,
        timeout_seconds=1.0,
        transport=transport,
        clock=clock,
    )
    return KeycloakAccountDirectory(
        base_url="http://keycloak.test",
        realm="sio",
        sio_api_client_id="sio-api",
        timeout_seconds=1.0,
        token_client=token_client,
        transport=transport,
    )


def _user(**overrides):
    body = {"id": SUB, "username": "compras.test", "enabled": True}
    body.update(overrides)
    return body


def test_get_account_uses_client_credentials_token(stub, directory):
    stub.routes[f"/admin/realms/sio/users/{SUB}"] = httpx.Response(200, json=_user())

    account = directory.get_account(SUB)

    assert account.sub == SUB and account.username == "compras.test"
    assert account.enabled is True and account.is_service_account is False
    assert stub.calls[0].headers["authorization"] == "Bearer tok-1"


def test_token_is_reused_until_30s_before_expiry(stub, directory, clock):
    stub.routes[f"/admin/realms/sio/users/{SUB}"] = httpx.Response(200, json=_user())

    directory.get_account(SUB)
    clock.now += 260  # quedan 40 s
    directory.get_account(SUB)
    assert stub.token_requests == 1

    clock.now += 15  # quedan 25 s: se renueva
    directory.get_account(SUB)
    assert stub.token_requests == 2


def test_get_account_404_is_none(directory):
    assert directory.get_account(SUB) is None


def test_disabled_and_service_accounts_are_reported(stub, directory):
    stub.routes[f"/admin/realms/sio/users/{SUB}"] = httpx.Response(
        200,
        json=_user(enabled=False, serviceAccountClientId="inventory-service"),
    )

    account = directory.get_account(SUB)

    assert account.enabled is False and account.is_service_account is True


def _search_route(results):
    def handler(request):
        assert request.url.params["username"] == "compras.test"
        assert request.url.params["exact"] == "true"
        return httpx.Response(200, json=results)

    return handler


def test_find_by_username_is_exact_and_normalized(stub, directory):
    stub.routes["/admin/realms/sio/users"] = _search_route([_user()])

    account = directory.find_account_by_username("  Compras.Test ")

    assert account.sub == SUB


def test_find_by_username_without_results_is_none(stub, directory):
    stub.routes["/admin/realms/sio/users"] = _search_route([])

    assert directory.find_account_by_username("compras.test") is None


def test_find_by_username_ambiguous_is_unavailable(stub, directory):
    stub.routes["/admin/realms/sio/users"] = _search_route([_user(), _user(id="otro")])

    with pytest.raises(DependencyUnavailableError) as error:
        directory.find_account_by_username("compras.test")

    assert error.value.provider == "keycloak"
    assert error.value.cause == "KEYCLOAK_AMBIGUOUS_USERNAME"


def test_permission_roles_resolve_client_once(stub, directory):
    client_lookups = []

    def clients(request):
        client_lookups.append(request.url.params["clientId"])
        return httpx.Response(200, json=[{"id": "uuid-sio-api", "clientId": "sio-api"}])

    stub.routes["/admin/realms/sio/clients"] = clients
    stub.routes[f"/admin/realms/sio/users/{SUB}/role-mappings/clients/uuid-sio-api/composite"] = httpx.Response(
        200,
        json=[{"name": "perm:inventory:all:all"}, {"name": "compras"}, {"sin": "nombre"}],
    )

    first = directory.get_permission_roles(SUB)
    second = directory.get_permission_roles(SUB)

    assert first == second == frozenset({"perm:inventory:all:all", "compras"})
    assert client_lookups == ["sio-api"]


@pytest.mark.parametrize("status", [403, 500, 503])
def test_admin_errors_are_dependency_unavailable(stub, directory, status):
    stub.routes[f"/admin/realms/sio/users/{SUB}"] = httpx.Response(status)

    with pytest.raises(DependencyUnavailableError) as error:
        directory.get_account(SUB)

    assert error.value.provider == "keycloak"


def test_401_retries_once_with_a_new_token_then_fails(stub, directory):
    stub.routes[f"/admin/realms/sio/users/{SUB}"] = httpx.Response(401)

    with pytest.raises(DependencyUnavailableError) as error:
        directory.get_account(SUB)

    assert stub.token_requests == 2
    assert error.value.cause == "KEYCLOAK_ADMIN_DENIED"


def test_rejected_token_is_dependency_unavailable(stub, directory):
    stub.token_status = 401

    with pytest.raises(DependencyUnavailableError) as error:
        directory.get_account(SUB)

    assert error.value.cause == "KEYCLOAK_TOKEN_REJECTED"


@pytest.mark.parametrize("exception", [httpx.ConnectError("sin red"), httpx.ReadTimeout("lento")])
def test_network_errors_are_dependency_unavailable(stub, directory, exception):
    def fail(request):
        raise exception

    stub.routes[f"/admin/realms/sio/users/{SUB}"] = fail

    with pytest.raises(DependencyUnavailableError):
        directory.get_account(SUB)


def test_unexpected_body_is_dependency_unavailable(stub, directory):
    stub.routes[f"/admin/realms/sio/users/{SUB}"] = httpx.Response(200, json={"id": SUB})

    with pytest.raises(DependencyUnavailableError):
        directory.get_account(SUB)


def test_secret_and_token_never_logged(stub, directory, caplog):
    stub.token_status = 500
    caplog.set_level(logging.DEBUG, logger=SERVICE_LOGGER)

    with pytest.raises(DependencyUnavailableError):
        directory.get_account(SUB)

    stub.token_status = 200
    stub.routes[f"/admin/realms/sio/users/{SUB}"] = httpx.Response(500)
    with pytest.raises(DependencyUnavailableError):
        directory.get_account(SUB)

    assert SECRET not in caplog.text
    assert "tok-" not in caplog.text
    assert SECRET not in repr(directory._token_client)


def test_service_account_detected_by_reserved_prefix(stub, directory):
    """Keycloak 26 no devuelve `serviceAccountClientId` en la Admin API (hallazgo de T091)."""
    stub.routes[f"/admin/realms/sio/users/{SUB}"] = httpx.Response(
        200,
        json={"id": SUB, "username": "service-account-inventory-service", "enabled": True},
    )

    assert directory.get_account(SUB).is_service_account is True


def test_regular_user_is_not_service_account(stub, directory):
    stub.routes[f"/admin/realms/sio/users/{SUB}"] = httpx.Response(200, json=_user())

    assert directory.get_account(SUB).is_service_account is False


def test_client_uuid_from_group_mappings_when_clients_listing_is_empty(stub, directory):
    """Con `query-clients` sin `view-clients`, Keycloak 26 lista los clientes vacíos (hallazgo de T091)."""
    stub.routes["/admin/realms/sio/clients"] = httpx.Response(200, json=[])
    stub.routes[f"/admin/realms/sio/users/{SUB}/role-mappings"] = httpx.Response(
        200, json={"clientMappings": {"account": {"id": "uuid-account", "mappings": []}}}
    )
    stub.routes[f"/admin/realms/sio/users/{SUB}/groups"] = httpx.Response(200, json=[{"id": "g-compras", "name": "compras"}])
    stub.routes["/admin/realms/sio/groups/g-compras/role-mappings"] = httpx.Response(
        200, json={"clientMappings": {"sio-api": {"id": "uuid-sio-api", "client": "sio-api", "mappings": []}}}
    )
    stub.routes[f"/admin/realms/sio/users/{SUB}/role-mappings/clients/uuid-sio-api/composite"] = httpx.Response(
        200, json=[{"name": "perm:purchase:all:all"}]
    )

    assert directory.get_permission_roles(SUB) == frozenset({"perm:purchase:all:all"})


def test_account_without_sio_api_roles_has_no_permissions(stub, directory):
    stub.routes["/admin/realms/sio/clients"] = httpx.Response(200, json=[])
    stub.routes[f"/admin/realms/sio/users/{SUB}/role-mappings"] = httpx.Response(200, json={})
    stub.routes[f"/admin/realms/sio/users/{SUB}/groups"] = httpx.Response(200, json=[])

    assert directory.get_permission_roles(SUB) == frozenset()
