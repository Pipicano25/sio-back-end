"""Autenticación y autorización por operación (RC-01, FR-002, FR-003; prueba obligatoria 13)."""

import dataclasses
import logging

import pytest
from fastapi.testclient import TestClient
from sio_auth import DENIED_PERMISSION_ATTRIBUTE, FORBIDDEN_DETAIL, LOGGER_NAME

from operational_context_service.main import create_app
from tests.conftest import ApiClient

ANY = "00000000-0000-4000-8000-000000000001"

# (método, ruta, recurso, acción) — las 12 operaciones de contracts/rest-api.md.
OPERATIONS = [
    ("GET", "/api/v1/companies", "companies", "read"),
    ("GET", f"/api/v1/companies/{ANY}", "companies", "read"),
    ("POST", "/api/v1/companies", "companies", "create"),
    ("PUT", f"/api/v1/companies/{ANY}", "companies", "update"),
    ("POST", f"/api/v1/companies/{ANY}/deactivate", "companies", "delete"),
    ("POST", f"/api/v1/companies/{ANY}/reactivate", "companies", "update"),
    ("GET", f"/api/v1/companies/{ANY}/branches", "branches", "read"),
    ("POST", f"/api/v1/companies/{ANY}/branches", "branches", "create"),
    ("GET", f"/api/v1/branches/{ANY}", "branches", "read"),
    ("PUT", f"/api/v1/branches/{ANY}", "branches", "update"),
    ("POST", f"/api/v1/branches/{ANY}/deactivate", "branches", "delete"),
    ("POST", f"/api/v1/branches/{ANY}/reactivate", "branches", "update"),
    # Fase B (specs/005-operational-context-users/contracts/rest-api.md).
    ("GET", f"/api/v1/companies/{ANY}/application-users", "application_users", "read"),
    ("POST", f"/api/v1/companies/{ANY}/application-users", "application_users", "create"),
    ("GET", f"/api/v1/application-users/{ANY}", "application_users", "read"),
    ("PUT", f"/api/v1/application-users/{ANY}", "application_users", "update"),
    ("POST", f"/api/v1/application-users/{ANY}/deactivate", "application_users", "delete"),
    ("POST", f"/api/v1/application-users/{ANY}/reactivate", "application_users", "update"),
    ("GET", f"/api/v1/application-users/{ANY}/user-branches", "user_branches", "read"),
    ("GET", f"/api/v1/branches/{ANY}/user-branches", "user_branches", "read"),
    ("POST", f"/api/v1/application-users/{ANY}/user-branches", "user_branches", "create"),
    ("GET", f"/api/v1/user-branches/{ANY}", "user_branches", "read"),
    ("POST", f"/api/v1/user-branches/{ANY}/deactivate", "user_branches", "delete"),
    ("POST", f"/api/v1/user-branches/{ANY}/reactivate", "user_branches", "update"),
    ("GET", f"/api/v1/companies/{ANY}/advisor-assignments", "company_advisor_assignments", "read"),
    ("POST", f"/api/v1/companies/{ANY}/advisor-assignments", "company_advisor_assignments", "create"),
    ("GET", f"/api/v1/advisor-assignments/{ANY}", "company_advisor_assignments", "read"),
    ("POST", f"/api/v1/advisor-assignments/{ANY}/close", "company_advisor_assignments", "delete"),
    ("POST", f"/api/v1/companies/{ANY}/advisor-assignments/change-primary", "company_advisor_assignments", "create"),
    ("GET", "/api/v1/me/operational-context", "application_users", "read"),
    ("GET", f"/api/v1/operational-access?company_id={ANY}", "application_users", "read"),
]

IDS = [f"{method} {path.replace(ANY, '{id}')}" for method, path, _, _ in OPERATIONS]


@pytest.mark.parametrize("method, path, resource, action", OPERATIONS, ids=IDS)
def test_without_token_is_401(anonymous, method, path, resource, action):
    response = anonymous.request(method, path, json={})

    assert response.status_code == 401
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.UNAUTHENTICATED"


@pytest.mark.parametrize("method, path, resource, action", OPERATIONS, ids=IDS)
def test_without_exact_permission_is_403(api_as, caplog, method, path, resource, action):
    other_actions = [a for a in ("read", "create", "update", "delete") if a != action]
    client = api_as(*[f"perm:operational-context:{resource}:{a}" for a in other_actions])

    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        response = client.request(method, path, json={})

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.FORBIDDEN"
    # El permiso exigido no se revela al cliente; queda solo en el log del servidor.
    assert body["detail"] == FORBIDDEN_DETAIL and "perm:" not in response.text
    denied = [getattr(r, DENIED_PERMISSION_ATTRIBUTE) for r in caplog.records if r.name == LOGGER_NAME]
    assert denied == [f"perm:operational-context:{resource}:{action}"]


@pytest.mark.parametrize("method, path, resource, action", OPERATIONS, ids=IDS)
def test_token_without_roles_is_403(api_as, method, path, resource, action):
    response = api_as().request(method, path, json={})

    assert response.status_code == 403


@pytest.mark.parametrize(
    "method, path, resource, action",
    [op for op in OPERATIONS if op[2] == "branches"],
    ids=[i for i, op in zip(IDS, OPERATIONS) if op[2] == "branches"],
)
def test_branch_routes_require_branch_permissions(api_as, method, path, resource, action):
    """Un token con todos los permisos de `companies` no alcanza para `branches`."""
    client = api_as("perm:operational-context:companies:all")

    assert client.request(method, path, json={}).status_code == 403


@pytest.mark.parametrize("path", ["/health/live", "/health/ready"])
def test_health_is_public(anonymous, path):
    assert anonymous.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_docs_public_when_enabled(anonymous, path):
    assert anonymous.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/docs", "/openapi.json"])
def test_docs_absent_when_disabled(test_settings, clean_database, test_auth, make_token, path):
    settings = dataclasses.replace(test_settings, docs_enabled=False)
    app = create_app(settings, auth=test_auth,
                     organization_directory_factory=lambda r: None,
                     geography_directory_factory=lambda r: None)
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get(path).status_code == 401
        admin = ApiClient(client, make_token("perm:operational-context:all:all"))
        assert admin.get(path).status_code == 404
