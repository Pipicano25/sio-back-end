"""Salud pública (Principio V; FR-023-80)."""

from __future__ import annotations


def test_live_and_ready(test_client, jwks_state) -> None:
    assert test_client.get("/health/live").json() == {"status": "ok"}
    assert test_client.get("/health/ready").status_code == 200
    jwks_state["available"] = False
    assert test_client.get("/health/ready").status_code == 503


def test_health_does_not_call_dependencies(test_client, fakes) -> None:
    test_client.get("/health/ready")
    assert fakes.log.calls == []
