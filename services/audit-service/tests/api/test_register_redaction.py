"""Redacción en Audit como defensa en profundidad (FR-017, RC-04, SC-005; T025)."""

from __future__ import annotations

import logging

from sqlalchemy import text

from tests.conftest import event_body

URL = "/api/v1/audit-events"
SECRET_1 = "api-key-valor-original"
SECRET_2 = "Contraseña-Original-123"


def test_sensitive_values_are_hidden_and_recorded(emitter, test_engine, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    body = event_body(
        new_values={"credentials": {"api_key": SECRET_1}, "Password": SECRET_2, "name": "visible"},
        previous_values={"contacts": [{"access-token": SECRET_1}]},
        redacted_paths=["new_values.ya_oculto"],
    )

    response = emitter.post(URL, json=body)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["new_values"] == {"credentials": "***", "Password": "***", "name": "visible"}
    assert data["previous_values"] == {"contacts": [{"access-token": "***"}]}
    assert data["redacted_paths"] == [
        "new_values.Password",
        "new_values.credentials",
        "new_values.ya_oculto",
        "previous_values.contacts[0].access-token",
    ]

    with test_engine.connect() as connection:
        stored = connection.execute(text("SELECT previous_values::text, new_values::text FROM audit_events")).one()

    for value in (SECRET_1, SECRET_2):
        assert value not in response.text
        assert value not in stored[0] and value not in stored[1]
        assert value not in caplog.text


def test_resend_of_event_redacted_by_emitter_is_idempotent(emitter) -> None:
    raw = event_body(new_values={"token": "t-original"})
    first = emitter.post(URL, json=raw)

    already_redacted = {**raw, "new_values": {"token": "***"}, "redacted_paths": ["new_values.token"]}
    second = emitter.post(URL, json=already_redacted)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_secret_never_rejected(emitter) -> None:
    response = emitter.post(URL, json=event_body(new_values={"client_secret": "x" * (70 * 1024)}))
    assert response.status_code == 201
    assert response.json()["new_values"] == {"client_secret": "***"}
