"""Rechazos sin evento, atomicidad y `seed` sin eventos en PC (feature 016; DS-02, RC-01, RC-06; T060)."""

from __future__ import annotations

from unittest.mock import patch


def test_rejections_record_no_event(api, api_as, anonymous, outbox) -> None:
    brand = api.post("/api/v1/brands", json={"code": "ACME", "name": "Acme"}).json()
    before = len(outbox())
    url = f"/api/v1/brands/{brand['id']}"

    assert anonymous.post("/api/v1/brands", json={"code": "OTRA", "name": "Otra"}).status_code == 401
    assert api_as("brands:read").put(url, json={"name": "X", "description": None, "version": 1}).status_code == 403
    assert api.put(url, json={"name": "X", "description": None, "version": 9}).status_code == 409
    assert api.post("/api/v1/brands", json={"code": "ACME", "name": "Duplicada"}).status_code == 409
    assert api.post("/api/v1/brands", json={"code": "", "name": ""}).status_code == 422

    assert len(outbox()) == before


def test_failure_after_recording_rolls_back_change_and_event(api, outbox) -> None:
    brand = api.post("/api/v1/brands", json={"code": "ACME", "name": "Acme"}).json()
    before = len(outbox())

    with patch(
        "product_catalog_service.application.audit_events.record_audit_event",
        side_effect=RuntimeError("fallo simulado al escribir la outbox"),
    ):
        response = api.put(f"/api/v1/brands/{brand['id']}", json={"name": "No se guarda", "description": None, "version": 1})

    assert response.status_code == 500  # el middleware de trazas responde el error interno

    assert len(outbox()) == before
    current = api.get(f"/api/v1/brands/{brand['id']}").json()
    assert current["name"] == "Acme" and current["version"] == 1


def test_seed_loading_records_no_event(session_factory, outbox) -> None:
    """La carga de datos iniciales no es una acción de usuario: sin autor, sin evento."""
    from product_catalog_service.seed.loader import load_seed

    before = len(outbox())
    with session_factory() as session:
        load_seed(session)

    assert len(outbox()) == before
