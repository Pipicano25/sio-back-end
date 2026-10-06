"""Autenticación y permisos de todas las rutas protegidas (Principio V, XIII; T012)."""

from __future__ import annotations

import pytest

from tests.api.routes import ROUTES

NOT_REVEALED = ("perm:", "audit:audit-events", "audit:platform-events")


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_without_token_401(as_token, method: str, path: str, permission: str) -> None:
    response = as_token(None).request(method, path, json={})
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "AUDIT.UNAUTHENTICATED"
    assert body["trace_id"]


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_invalid_token_401(as_token, method: str, path: str, permission: str) -> None:
    response = as_token("no-es-un-jwt").request(method, path, json={})
    assert response.status_code == 401


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_without_permission_403_does_not_reveal_it(
    as_user, method: str, path: str, permission: str
) -> None:
    response = as_user("inventario.test").request(method, path, json={})
    assert response.status_code == 403
    assert response.json()["code"] == "AUDIT.FORBIDDEN"
    assert not any(marker in response.text for marker in NOT_REVEALED)


@pytest.mark.parametrize(
    ("method", "path", "permission"),
    [route for route in ROUTES if route[2] == "perm:audit:platform-events:read"],
)
def test_company_permission_does_not_open_platform(
    as_user, method: str, path: str, permission: str
) -> None:
    # `auditor.sin-oc` tiene solo `perm:audit:audit-events:read` (RC-10).
    assert as_user("auditor.sin-oc").request(method, path).status_code == 403
