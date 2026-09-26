"""Salud del servicio y rutas públicas (Principio V)."""

from fastapi.testclient import TestClient

from product_catalog_service.config import Settings
from product_catalog_service.main import create_app


def test_live_is_public(anonymous) -> None:
    response = anonymous.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_is_public_when_database_available(anonymous) -> None:
    response = anonymous.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_503_without_details_when_database_down(test_auth) -> None:
    settings = Settings(
        docs_enabled=False,
        database_url="postgresql+psycopg://nobody:nothing@127.0.0.1:1/none?connect_timeout=1",
        party_identity_service_base_url="http://party-identity.test",
        party_identity_timeout_seconds=1.0,
    )
    with TestClient(create_app(settings, auth=test_auth)) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_docs_public_only_when_enabled(anonymous, test_auth) -> None:
    assert anonymous.get("/openapi.json").status_code == 200

    settings = Settings(
        docs_enabled=False,
        database_url="postgresql+psycopg://nobody:nothing@127.0.0.1:1/none",
        party_identity_service_base_url="http://party-identity.test",
        party_identity_timeout_seconds=1.0,
    )
    with TestClient(create_app(settings, auth=test_auth)) as client:
        assert client.get("/openapi.json").status_code == 401
        assert client.get("/docs").status_code == 401
