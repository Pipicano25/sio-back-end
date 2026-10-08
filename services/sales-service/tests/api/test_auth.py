"""Autenticación, usuario humano y métodos (RC-05; T015)."""

from __future__ import annotations

import pytest

from tests.api.routes import ROUTES, fill

SERVICE_ACCOUNT_ROLES = ("perm:all:all:all", "perm:sales:all:all")


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_without_token_401(as_token, method, path, permission) -> None:
    response = as_token(None).request(method, fill(path), json={})
    assert response.status_code == 401
    assert response.json()["code"] == "SALES.UNAUTHENTICATED"


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_service_account_gets_403_even_with_wildcards(as_token, service_token, user_token, world, method, path, permission) -> None:
    """Ningún token técnico (ni el propio sales-service) usa la API de ventas (RC-05)."""
    technical = as_token(service_token(*SERVICE_ACCOUNT_ROLES, client_id="sales-service"))
    response = technical.request(method, fill(path, world.company), json={})
    assert response.status_code == 403, response.text
    no_permission = as_token(user_token("compras.test")).request(method, fill(path, world.company), json={})
    assert no_permission.status_code == 403
    assert response.json()["detail"] == no_permission.json()["detail"]  # mismo cuerpo, sin revelar el motivo


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_permission_is_required(make_token, as_token, world, method, path, permission) -> None:
    unrelated = make_token("perm:inventory:all:all", sub="sub-sin-permiso", preferred_username="sin.permiso")
    response = as_token(unrelated).request(method, fill(path, world.company), json={})
    assert response.status_code == 403
    assert "perm:" not in response.text


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("DELETE", "/api/v1/companies/{company}/sales/{sale}"),
        ("PATCH", "/api/v1/companies/{company}/sales/{sale}"),
        ("DELETE", "/api/v1/companies/{company}/sale-sequences/{sequence}"),
        ("PUT", "/api/v1/companies/{company}/sales/{sale}/availability"),
        ("DELETE", "/api/v1/companies/{company}/sale-operations/{operation}"),
    ],
)
def test_undeclared_methods_405(seller, world, method, path) -> None:
    assert seller.request(method, fill(path, world.company)).status_code == 405


@pytest.mark.parametrize(("method", "path", "permission"), ROUTES)
def test_profitability_permission_alone_opens_no_route(make_token, as_token, world, method, path, permission) -> None:
    """`read-profitability` solo decide qué campos se ven; no autoriza ninguna ruta (DS-12)."""
    only = make_token("perm:sales:sales:read-profitability", sub="sub-solo-rentabilidad", preferred_username="solo")
    assert as_token(only).request(method, fill(path, world.company), json={}).status_code == 403
