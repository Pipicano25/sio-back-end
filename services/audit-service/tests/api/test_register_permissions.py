"""Solo cuentas de servicio registran eventos (RC-01; T026)."""

from __future__ import annotations

import pytest

from tests.conftest import CREATE, event_body

URLS = ["/api/v1/audit-events", "/api/v1/audit-events/batch"]


def _payload(url: str) -> dict:
    return {"events": [event_body()]} if url.endswith("batch") else event_body()


@pytest.mark.parametrize("url", URLS)
@pytest.mark.parametrize("username", ["admin.test", "supervisor.test"])
def test_humans_with_wildcards_are_forbidden(as_user, as_token, service_token, url, username) -> None:
    human = as_user(username).post(url, json=_payload(url))
    missing = as_token(service_token("perm:audit:audit-events:read")).post(url, json=_payload(url))

    assert human.status_code == 403
    # El cuerpo es idéntico al de la falta de permiso: no revela el motivo.
    assert {k: v for k, v in human.json().items() if k != "trace_id"} == {
        k: v for k, v in missing.json().items() if k != "trace_id"
    }
    assert "perm:" not in human.text and "service-account" not in human.text


@pytest.mark.parametrize("url", URLS)
def test_human_token_with_explicit_create_is_forbidden(as_token, make_token, url) -> None:
    token = make_token(CREATE, sub="sub-humano", preferred_username="humano")
    assert as_token(token).post(url, json=_payload(url)).status_code == 403


@pytest.mark.parametrize("url", URLS)
def test_service_account_without_permission_is_forbidden(as_token, service_token, url) -> None:
    assert as_token(service_token()).post(url, json=_payload(url)).status_code == 403


def test_forbidden_before_validation(as_user) -> None:
    response = as_user("admin.test").post("/api/v1/audit-events", json={"invalido": True})
    assert response.status_code == 403
