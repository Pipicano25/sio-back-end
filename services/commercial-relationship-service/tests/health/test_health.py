"""Salud pública sin detalles internos (Principio V, FR-080)."""

from __future__ import annotations

from sqlalchemy.exc import OperationalError


def test_live_is_public(as_token):
    response = as_token(None).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_is_public_and_does_not_call_providers(as_token, fake_oc, fake_catalog, fake_party):
    response = as_token(None).get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert fake_oc.access_calls == [] and fake_catalog.lookup_calls == [] and fake_party.calls == []


def test_ready_without_database_is_503_without_details(as_token, app, monkeypatch):
    def fail():
        raise OperationalError("SELECT 1", {}, Exception("conexión rechazada en 10.0.0.1"))

    monkeypatch.setattr(app.state.database, "check_connection", fail)
    response = as_token(None).get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
