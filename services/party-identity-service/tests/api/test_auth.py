"""Pruebas de autenticación y permisos por operación (RC-01, FR-002, FR-003).

Cada una de las 18 operaciones de `contracts/rest-api.md` exige token y el
permiso exacto `perm:party-identity:{recurso}:{accion}`.
"""

import pytest
from fastapi.testclient import TestClient

from party_identity_service.main import create_app
from tests.conftest import ApiClient, random_uuid

ID = "00000000-0000-0000-0000-000000000001"
VERSION_BODY = {"version": 1}

OPERATIONS = [
    ("GET", "/api/v1/identification-type-rules", None, "identification_type_rules", "read"),
    ("GET", f"/api/v1/identification-type-rules/{ID}", None, "identification_type_rules", "read"),
    ("POST", "/api/v1/identification-type-rules", {}, "identification_type_rules", "create"),
    ("PUT", f"/api/v1/identification-type-rules/{ID}", {}, "identification_type_rules", "update"),
    ("POST", f"/api/v1/identification-type-rules/{ID}/versions", {}, "identification_type_rules", "create"),
    ("POST", f"/api/v1/identification-type-rules/{ID}/deactivate", VERSION_BODY, "identification_type_rules", "delete"),
    ("GET", "/api/v1/person-identities", None, "person_identities", "read"),
    ("GET", f"/api/v1/person-identities/{ID}", None, "person_identities", "read"),
    ("POST", "/api/v1/person-identities", {}, "person_identities", "create"),
    ("PUT", f"/api/v1/person-identities/{ID}", {}, "person_identities", "update"),
    ("POST", f"/api/v1/person-identities/{ID}/deactivate", VERSION_BODY, "person_identities", "delete"),
    ("POST", f"/api/v1/person-identities/{ID}/reactivate", VERSION_BODY, "person_identities", "update"),
    ("GET", "/api/v1/organization-identities", None, "organization_identities", "read"),
    ("GET", f"/api/v1/organization-identities/{ID}", None, "organization_identities", "read"),
    ("POST", "/api/v1/organization-identities", {}, "organization_identities", "create"),
    ("PUT", f"/api/v1/organization-identities/{ID}", {}, "organization_identities", "update"),
    ("POST", f"/api/v1/organization-identities/{ID}/deactivate", VERSION_BODY, "organization_identities", "delete"),
    ("POST", f"/api/v1/organization-identities/{ID}/reactivate", VERSION_BODY, "organization_identities", "update"),
]
IDS = [f"{method} {path.replace(ID, '{id}')}" for method, path, *_ in OPERATIONS]
ACTIONS = ("read", "create", "update", "delete")


@pytest.mark.parametrize(("method", "path", "body", "resource", "action"), OPERATIONS, ids=IDS)
def test_without_token_is_unauthenticated(anonymous, method, path, body, resource, action) -> None:
    response = anonymous.request(method, path, json=body)

    assert response.status_code == 401
    assert response.json()["code"] == "PARTY_IDENTITY.UNAUTHENTICATED"


@pytest.mark.parametrize(("method", "path", "body", "resource", "action"), OPERATIONS, ids=IDS)
def test_without_exact_permission_is_forbidden(api_as, method, path, body, resource, action) -> None:
    """Un token con todos los demás permisos del recurso no basta."""
    other_permissions = [
        f"perm:party-identity:{resource}:{other}"
        for other in ACTIONS
        if other != action
    ]
    response = api_as(*other_permissions).request(method, path, json=body)

    assert response.status_code == 403
    assert response.json()["code"] == "PARTY_IDENTITY.FORBIDDEN"


@pytest.mark.parametrize(("method", "path", "body", "resource", "action"), OPERATIONS, ids=IDS)
def test_with_exact_permission_passes_authorization(api_as, method, path, body, resource, action) -> None:
    response = api_as(f"perm:party-identity:{resource}:{action}").request(method, path, json=body)

    assert response.status_code not in {401, 403}


def test_other_service_permission_is_forbidden(api_as) -> None:
    response = api_as("perm:geography:all:read").get(f"/api/v1/person-identities/{random_uuid()}")

    assert response.status_code == 403


def test_health_is_public(anonymous) -> None:
    assert anonymous.get("/health/live").status_code == 200
    assert anonymous.get("/health/ready").status_code == 200


def test_docs_are_public_when_enabled(anonymous) -> None:
    assert anonymous.get("/openapi.json").status_code == 200
    assert anonymous.get("/docs").status_code == 200


def test_docs_are_not_exposed_when_disabled(test_settings, test_auth, fake_countries) -> None:
    settings = type(test_settings)(
        docs_enabled=False,
        database_url=test_settings.database_url,
        geography_service_base_url=test_settings.geography_service_base_url,
    )
    app = create_app(settings, auth=test_auth, country_directory_factory=lambda request: fake_countries)

    with TestClient(app) as client:
        anonymous = ApiClient(client, None)
        assert anonymous.get("/openapi.json").status_code in {401, 404}
        assert anonymous.get("/docs").status_code in {401, 404}
