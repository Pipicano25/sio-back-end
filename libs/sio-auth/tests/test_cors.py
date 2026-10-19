"""CORS abierto (0.5.0): cualquier origen, sin credenciales y sin debilitar la autenticación."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient
from pydantic import BaseModel

from sio_auth import AuthSettings, SIOAuth, install_cors

ISSUER = "http://issuer.test/realms/sio"
KID = "kid-pruebas"
ORIGINS = ["https://app.example.com", "http://localhost:5173", "https://otro-pais.example.co"]

_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class _StaticJWKS:
    def get_signing_key(self, kid: str):
        return _KEY.public_key()

    def close(self) -> None:
        pass


def _token(roles: list[str], *, key=_KEY) -> str:
    payload = {
        "sub": "sub-1",
        "iss": ISSUER,
        "aud": "sio-api",
        "exp": int(time.time()) + 300,
        "resource_access": {"sio-api": {"roles": roles}},
    }
    return jwt.encode(payload, key, algorithm="RS256", headers={"kid": KID})


class _Body(BaseModel):
    name: str


def _app() -> FastAPI:
    auth = SIOAuth(AuthSettings(issuer=ISSUER), jwks_client=_StaticJWKS())
    app = FastAPI()

    @app.get("/health/live")
    def live():
        return {"status": "ok"}

    @app.get("/items", dependencies=[auth.permission("demo", "items", "read")])
    def list_items():
        return {"items": []}

    @app.post(
        "/items",
        status_code=201,
        dependencies=[auth.permission("demo", "items", "create")],
    )
    def create_item(body: _Body, idempotency_key: str = Header(alias="Idempotency-Key")):
        return {"name": body.name, "idempotency_key": idempotency_key}

    @app.get("/boom", dependencies=[auth.permission("demo", "items", "read")])
    def boom():
        raise RuntimeError("fallo no controlado")

    auth.protect(app, public_paths={"/health/live"})
    install_cors(app)
    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_app(), raise_server_exceptions=False)


def _assert_cors(response) -> None:
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers
    exposed = response.headers.get("access-control-expose-headers", "")
    assert "X-Trace-Id" in exposed and "Content-Disposition" in exposed


@pytest.mark.parametrize("origin", ORIGINS)
@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE"])
def test_preflight_from_any_origin_without_token(client, origin, method):
    response = client.options(
        "/items",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "authorization, content-type, idempotency-key, traceparent",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers
    assert method in response.headers["access-control-allow-methods"]
    allowed = response.headers["access-control-allow-headers"].lower()
    for header in ("authorization", "content-type", "idempotency-key", "traceparent"):
        assert header in allowed
    assert response.headers["access-control-max-age"] == "600"


def test_options_without_preflight_headers_is_still_authenticated(client):
    # Un OPTIONS que no es preflight (sin Access-Control-Request-Method) no se salta sio-auth.
    response = client.options("/items", headers={"Origin": ORIGINS[0]})

    assert response.status_code == 401
    _assert_cors(response)


@pytest.mark.parametrize("origin", ORIGINS)
def test_missing_token_is_401_with_cors(client, origin):
    response = client.get("/items", headers={"Origin": origin})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    _assert_cors(response)


@pytest.mark.parametrize(
    "authorization",
    ["Bearer no-es-un-jwt", "Basic dXNlcjpwYXNz", f"Bearer {_token(['perm:demo:items:read'], key=_OTHER_KEY)}"],
)
def test_invalid_token_is_401_with_cors(client, authorization):
    response = client.get("/items", headers={"Origin": ORIGINS[0], "Authorization": authorization})

    assert response.status_code == 401
    _assert_cors(response)


def test_valid_token_without_permission_is_403_with_cors(client):
    response = client.get(
        "/items",
        headers={"Origin": ORIGINS[1], "Authorization": f"Bearer {_token(['perm:otro:items:read'])}"},
    )

    assert response.status_code == 403
    _assert_cors(response)


def test_authorized_read_is_200_with_cors(client):
    response = client.get(
        "/items",
        headers={"Origin": ORIGINS[2], "Authorization": f"Bearer {_token(['perm:demo:items:read'])}"},
    )

    assert response.status_code == 200
    assert response.json() == {"items": []}
    _assert_cors(response)


def test_authorized_write_with_idempotency_key_is_201_with_cors(client):
    response = client.post(
        "/items",
        json={"name": "uno"},
        headers={
            "Origin": ORIGINS[0],
            "Authorization": f"Bearer {_token(['perm:demo:items:create'])}",
            "Content-Type": "application/json",
            "Idempotency-Key": "clave-1",
        },
    )

    assert response.status_code == 201
    assert response.json() == {"name": "uno", "idempotency_key": "clave-1"}
    _assert_cors(response)


def test_validation_error_is_422_with_cors(client):
    response = client.post(
        "/items",
        json={},
        headers={
            "Origin": ORIGINS[0],
            "Authorization": f"Bearer {_token(['perm:demo:items:create'])}",
            "Idempotency-Key": "clave-2",
        },
    )

    assert response.status_code == 422
    _assert_cors(response)


def test_not_found_is_404_with_cors(client):
    response = client.get(
        "/no-existe",
        headers={"Origin": ORIGINS[0], "Authorization": f"Bearer {_token([])}"},
    )

    assert response.status_code == 404
    _assert_cors(response)


def test_unhandled_error_is_500_with_cors(client):
    response = client.get(
        "/boom",
        headers={"Origin": ORIGINS[0], "Authorization": f"Bearer {_token(['perm:demo:items:read'])}"},
    )

    assert response.status_code == 500
    _assert_cors(response)


def test_public_route_has_cors(client):
    response = client.get("/health/live", headers={"Origin": ORIGINS[0]})

    assert response.status_code == 200
    _assert_cors(response)


def test_cookies_never_turn_into_credentials(client):
    response = client.get(
        "/health/live",
        headers={"Origin": ORIGINS[0], "Cookie": "sesion=abc"},
    )

    assert "access-control-allow-credentials" not in response.headers


def test_request_without_origin_has_no_cors_headers(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_install_cors_is_idempotent():
    app = _app()
    install_cors(app)
    client = TestClient(app)

    response = client.get("/health/live", headers={"Origin": ORIGINS[0]})

    assert response.headers.get_list("access-control-allow-origin") == ["*"]


def test_install_cors_after_startup_is_rejected():
    app = FastAPI()
    TestClient(app).get("/")

    with pytest.raises(RuntimeError):
        install_cors(app)
