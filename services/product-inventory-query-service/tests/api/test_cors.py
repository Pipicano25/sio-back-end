"""CORS abierto (sio-auth 0.5.0) sobre la aplicación real de product-inventory-query-service.

Cualquier origen web recibe `Access-Control-Allow-Origin: *`, nunca credenciales; el
preflight se responde sin token y la autenticación y los permisos no cambian.
"""

from __future__ import annotations

import re
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sio_auth.middleware import SIOAuthMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.errors import ServerErrorMiddleware

ORIGINS = ("https://app.example.com", "http://localhost:5173", "https://erp.otro-pais.example.co")
REQUEST_HEADERS = "authorization, content-type, idempotency-key, traceparent"
ALL_PERMISSIONS = "perm:all:all:all"
BOOM_PATH = "/__cors-boom"
TRACEPARENT = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"


def _public_paths(app: FastAPI) -> frozenset[str]:
    for middleware in app.user_middleware:
        if middleware.cls is SIOAuthMiddleware:
            return frozenset(middleware.kwargs["public_paths"])
    raise AssertionError("la aplicación no usa SIOAuthMiddleware")


def _protected_operations(app: FastAPI) -> list[tuple[str, str]]:
    public = _public_paths(app) | {BOOM_PATH}
    operations = []
    for template, path_item in app.openapi()["paths"].items():
        if template in public:
            continue
        path = re.sub(r"\{[^}]+\}", str(uuid4()), template)
        operations.extend((method.upper(), path) for method in sorted(path_item) if method != "head")
    assert operations
    return operations


def _assert_cors(response) -> None:
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers
    exposed = response.headers.get("access-control-expose-headers", "")
    assert "X-Trace-Id" in exposed and "Content-Disposition" in exposed


@pytest.fixture
def cors_client(app: FastAPI) -> Generator[TestClient, None, None]:
    def boom() -> None:
        raise RuntimeError("fallo no controlado de prueba")

    app.add_api_route(BOOM_PATH, boom, methods=["GET"])
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def authorized_get(world, user_token) -> tuple[str, str]:
    """Lectura que el usuario autorizado puede hacer sin datos previos: ruta y token."""
    return f"{world.base}/inventory-summary", user_token("admin.test")


def test_cors_wraps_the_whole_stack(cors_client):
    cors_client.get("/health/live")
    stack = cors_client.app.middleware_stack

    assert isinstance(stack, CORSMiddleware)
    assert isinstance(stack.app, ServerErrorMiddleware)


@pytest.mark.parametrize("origin", ORIGINS)
def test_every_route_answers_preflight_without_token(cors_client, origin):
    for method, path in _protected_operations(cors_client.app):
        response = cors_client.options(
            path,
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": REQUEST_HEADERS,
            },
        )

        assert response.status_code == 200, (method, path)
        assert response.headers["access-control-allow-origin"] == "*"
        assert "access-control-allow-credentials" not in response.headers
        assert method in response.headers["access-control-allow-methods"]
        allowed = response.headers["access-control-allow-headers"].lower()
        for header in ("authorization", "content-type", "idempotency-key", "traceparent"):
            assert header in allowed


def test_every_protected_route_without_token_is_401_with_cors(cors_client):
    for method, path in _protected_operations(cors_client.app):
        response = cors_client.request(method, path, headers={"Origin": ORIGINS[0]})

        assert response.status_code == 401, (method, path)
        _assert_cors(response)


@pytest.mark.parametrize("authorization", ["Bearer no-es-un-jwt", "Basic dXNlcjpwYXNz", "Bearer "])
def test_invalid_token_is_401_with_cors(cors_client, authorization):
    method, path = _protected_operations(cors_client.app)[0]

    response = cors_client.request(method, path, headers={"Origin": ORIGINS[1], "Authorization": authorization})

    assert response.status_code == 401
    _assert_cors(response)


def test_every_route_without_permission_is_403_with_cors(cors_client, make_token):
    headers = {"Origin": ORIGINS[2], "Authorization": f"Bearer {make_token()}"}

    for method, path in _protected_operations(cors_client.app):
        response = cors_client.request(method, path, headers=headers)

        assert response.status_code == 403, (method, path)
        _assert_cors(response)


def test_unknown_route_is_404_with_cors(cors_client, make_token):
    response = cors_client.get(
        "/no-existe", headers={"Origin": ORIGINS[0], "Authorization": f"Bearer {make_token(ALL_PERMISSIONS)}"}
    )

    assert response.status_code == 404
    _assert_cors(response)


def test_unhandled_error_is_500_with_cors(cors_client, make_token):
    response = cors_client.get(
        BOOM_PATH, headers={"Origin": ORIGINS[0], "Authorization": f"Bearer {make_token(ALL_PERMISSIONS)}"}
    )

    assert response.status_code == 500
    _assert_cors(response)


def test_public_health_has_cors(cors_client):
    response = cors_client.get("/health/live", headers={"Origin": ORIGINS[0]})

    assert response.status_code == 200
    _assert_cors(response)


def test_request_without_origin_has_no_cors_headers(cors_client):
    response = cors_client.get("/health/live")

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_authorized_requests_behave_the_same_with_and_without_origin(cors_client, make_token):
    token = make_token(ALL_PERMISSIONS)
    statuses = {}

    for method, path in _protected_operations(cors_client.app):
        if method != "GET":
            continue
        base = {"Authorization": f"Bearer {token}", "traceparent": TRACEPARENT}
        without_origin = cors_client.request(method, path, headers=base)
        with_origin = cors_client.request(method, path, headers={**base, "Origin": ORIGINS[0]})

        assert with_origin.status_code == without_origin.status_code, (method, path)
        assert with_origin.content == without_origin.content, (method, path)
        assert with_origin.headers.get("x-trace-id") == without_origin.headers.get("x-trace-id")
        assert "access-control-allow-origin" not in without_origin.headers
        _assert_cors(with_origin)
        statuses[(method, path)] = with_origin.status_code

    assert statuses


def test_authorized_request_returns_200_with_cors(cors_client, authorized_get):
    path, token = authorized_get

    response = cors_client.get(path, headers={"Origin": ORIGINS[1], "Authorization": f"Bearer {token}"})

    assert response.status_code == 200, response.text
    _assert_cors(response)
