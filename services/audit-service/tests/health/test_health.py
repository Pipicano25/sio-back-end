"""Salud y documentación (Principio V; T012)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from audit_service.main import create_app


def test_live_is_public(as_token) -> None:
    response = as_token(None).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_is_public_without_details(as_token) -> None:
    response = as_token(None).get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_docs_only_when_enabled(test_settings, test_auth, fake_oc, clean_database) -> None:
    with TestClient(create_app(test_settings, auth=test_auth, access_directory_factory=fake_oc.access_for)) as client:
        assert client.get("/openapi.json").status_code == 200
        assert client.get("/docs").status_code == 200

    disabled = test_settings.__class__(
        docs_enabled=False,
        database_url=test_settings.database_url,
        operational_context_base_url=test_settings.operational_context_base_url,
    )
    with TestClient(create_app(disabled, auth=test_auth, access_directory_factory=fake_oc.access_for)) as client:
        assert client.get("/openapi.json").status_code == 401
        assert client.get("/docs").status_code == 401
