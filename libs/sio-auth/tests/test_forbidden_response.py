"""El `403` por permiso no revela el permiso exigido; el permiso solo va al log (0.4.0)."""

import logging
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from sio_auth import (
    DENIED_PERMISSION_ATTRIBUTE,
    FORBIDDEN_DETAIL,
    LOGGER_NAME,
    AuthSettings,
    SIOAuth,
)
from sio_auth.permissions import extract_permission_grants
from sio_auth.tokens import TokenClaims


def _client(roles: list[str]) -> TestClient:
    auth = SIOAuth(AuthSettings(issuer="http://issuer.test/realms/sio"), jwks_client=object())
    app = FastAPI()

    @app.middleware("http")
    async def inject_claims(request: Request, call_next):
        # Sustituye al middleware de sio-auth: claims ya validados con estos roles.
        request.state.sio_claims = TokenClaims(
            subject="sub-1",
            issuer="http://issuer.test/realms/sio",
            audiences=("sio-api",),
            expires_at=datetime.now(timezone.utc),
            roles=frozenset(roles),
            permissions=extract_permission_grants(roles),
            preferred_username="usuario.prueba",
            email=None,
            raw={},
        )
        return await call_next(request)

    @app.post("/movements", dependencies=[auth.permission("inventory", "movements", "create")])
    def create():
        return {"ok": True}

    return TestClient(app)


@pytest.mark.parametrize("roles", [[], ["perm:inventory:movements:read"], ["perm:all:all:read"]])
def test_forbidden_detail_does_not_reveal_the_permission(roles):
    response = _client(roles).post("/movements")

    assert response.status_code == 403
    assert response.json() == {"detail": FORBIDDEN_DETAIL}
    for leaked in ("perm:", "inventory", "movements", "create"):
        assert leaked not in response.text


def test_forbidden_detail_is_descriptive():
    assert "no tiene permiso" in FORBIDDEN_DETAIL
    assert "administrador" in FORBIDDEN_DETAIL
    assert "trace_id" in FORBIDDEN_DETAIL


def test_denied_permission_is_logged_server_side(caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        _client(["perm:inventory:movements:read"]).post("/movements")

    records = [record for record in caplog.records if record.name == LOGGER_NAME]
    assert len(records) == 1
    assert getattr(records[0], DENIED_PERMISSION_ATTRIBUTE) == "perm:inventory:movements:create"
    message = records[0].getMessage()
    assert "permiso_requerido=perm:inventory:movements:create" in message
    assert "sujeto=sub-1" in message and "metodo=POST" in message and "ruta=/movements" in message


def test_granted_permission_passes_without_log(caplog):
    with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
        response = _client(["perm:inventory:all:all"]).post("/movements")

    assert response.status_code == 200
    assert not [record for record in caplog.records if record.name == LOGGER_NAME]
