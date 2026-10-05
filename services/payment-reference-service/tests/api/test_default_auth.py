"""FR-043 (N-04): sin doble inyectado, la aplicación usa la autenticación real y protege sus rutas."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from payment_reference_service.api import security
from payment_reference_service.main import create_app
from tests.conftest import ADMIN, CONDITION_TYPES


@pytest.fixture(scope="module")
def default_client():
    with TestClient(create_app()) as client:
        yield client


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", CONDITION_TYPES),
        ("POST", CONDITION_TYPES),
        ("GET", f"{CONDITION_TYPES}/00000000-0000-4000-8000-000000000001"),
        ("POST", f"{CONDITION_TYPES}/00000000-0000-4000-8000-000000000001/deactivate"),
        ("GET", "/global-payment-methods"),
    ],
)
def test_default_app_rejects_requests_without_token(default_client, method, path):
    response = default_client.request(method, path)

    assert response.status_code == 401


def test_default_app_does_not_trust_the_test_double(default_client, make_token):
    """Un token que el doble de pruebas acepta no vale para la autenticación real (otro JWKS)."""
    token = make_token(ADMIN)

    response = default_client.get(CONDITION_TYPES, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_default_auth_is_the_real_instance_built_from_environment():
    assert isinstance(security.auth, security.SIOAuth)
    assert security.auth.settings.issuer.endswith("/realms/sio")
