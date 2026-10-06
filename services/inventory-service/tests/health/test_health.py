"""Salud y documentación (Principio V; T012)."""

from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from inventory_service.main import create_app


def test_live_is_public(as_token) -> None:
    response = as_token(None).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_is_public_without_details(as_token) -> None:
    response = as_token(None).get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_docs_only_when_enabled(test_settings, test_auth, fake_oc, fake_cr, clean_database) -> None:
    factories = {
        "auth": test_auth,
        "operational_context_factory": fake_oc.directory,
        "commercial_relationship_factory": fake_cr.directory,
        "access_directory_factory": fake_oc.access_for,
    }
    with TestClient(create_app(test_settings, **factories)) as client:
        assert client.get("/openapi.json").status_code == 200
        assert client.get("/docs").status_code == 200

    with TestClient(create_app(replace(test_settings, docs_enabled=False), **factories)) as client:
        assert client.get("/openapi.json").status_code in (401, 404)
        assert client.get("/docs").status_code in (401, 404)
