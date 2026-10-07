"""Autenticación y permisos de todas las rutas protegidas (Principio V, XIII; T012)."""

from __future__ import annotations

import pytest

from tests.api.routes import ROUTES, declared_methods

NOT_REVEALED = ("perm:", "inventory:entries", "inventory:outputs", "inventory:balances", "inventory:movements")


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_without_token_401(as_token, method: str, path: str, permission: str) -> None:
    response = as_token(None).request(method, path, json={})
    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "INVENTORY.UNAUTHENTICATED"
    assert body["trace_id"]


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_invalid_token_401(as_token, method: str, path: str, permission: str) -> None:
    assert as_token("no-es-un-jwt").request(method, path, json={}).status_code == 401


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_without_permission_403_does_not_reveal_it(as_user, method: str, path: str, permission: str) -> None:
    response = as_user("compras.test").request(method, path, json={})
    assert response.status_code == 403
    assert response.json()["code"] == "INVENTORY.FORBIDDEN"
    assert not any(marker in response.text for marker in NOT_REVEALED)


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_mutation_methods_are_not_published(operator, method: str, path: str, permission: str) -> None:
    # 013 publica `PUT` en las rutas 16, 23 y 27; todo método no declarado sigue en `405`.
    for verb in {"PUT", "PATCH", "DELETE"} - declared_methods(path):
        assert operator.request(verb, path, json={}).status_code == 405
