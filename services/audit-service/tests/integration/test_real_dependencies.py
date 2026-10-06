"""Integración real con Keycloak y Operational Context (T066).

Ejecutar con `pytest -m integration` con el entorno integrado en marcha (audit-service en
`AUDIT_INTEGRATION_BASE_URL`, Operational Context y Keycloak reconstruido desde la plantilla con el
cliente `audit-test-emitter`). Registra eventos ficticios; no los elimina (son inmutables).

Detiene y vuelve a iniciar `sio-operational-context-service` en la última prueba.
"""

from __future__ import annotations

import subprocess
import time
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest

from tests.integration.support import (
    AUDIT,
    EMITTER,
    OPERATIONAL_CONTEXT,
    admin_member_company,
    emitter_client,
    require_audit,
    user_client,
)

pytestmark = pytest.mark.integration


def _event(**changes) -> dict:
    body = {
        "event_id": str(uuid4()),
        "action": "CHANGE_PRICE",
        "entity_type": "PriceListItem",
        "entity_id": str(uuid4()),
        "previous_values": {"unit_price": "2000.00"},
        "new_values": {"unit_price": "2100.00", "client_secret": "nunca-se-guarda"},
        "result": "SUCCESS",
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    body.update(changes)
    return body


@pytest.fixture(scope="module")
def emitter():
    require_audit()
    with emitter_client() as client:
        yield client


@pytest.fixture(scope="module")
def admin():
    with user_client("admin.test") as client:
        yield client


@pytest.fixture(scope="module")
def company(admin):
    return admin_member_company(admin)


def test_register_with_real_technical_identity(emitter, admin, company) -> None:
    body = _event(company_id=str(company))
    response = emitter.post(f"{AUDIT}/audit-events", json=body)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["source_service"] == EMITTER
    assert data["new_values"]["client_secret"] == "***"
    assert data["redacted_paths"] == ["new_values.client_secret"]

    again = emitter.post(f"{AUDIT}/audit-events", json=body)
    assert again.status_code == 200 and again.json()["id"] == data["id"]

    listed = admin.get(f"{AUDIT}/companies/{company}/audit-events", params={"event_id": body["event_id"]})
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["items"]] == [data["id"]]


@pytest.mark.parametrize("username", ["admin.test", "supervisor.test"])
def test_real_humans_cannot_register(username) -> None:
    require_audit()
    with user_client(username) as client:
        response = client.post(f"{AUDIT}/audit-events", json=_event())
    assert response.status_code == 403
    assert "perm:" not in response.text


def test_non_member_company_is_404(admin) -> None:
    require_audit()
    assert admin.get(f"{AUDIT}/companies/{uuid4()}/audit-events").status_code == 404


def test_user_without_audit_permission_is_403(company) -> None:
    require_audit()
    with user_client("inventario.test") as client:
        assert client.get(f"{AUDIT}/companies/{company}/audit-events").status_code == 403


def test_platform_events_with_supervisor(emitter) -> None:
    platform = emitter.post(f"{AUDIT}/audit-events", json=_event(entity_type="GlobalProduct"))
    assert platform.status_code == 201

    with user_client("supervisor.test") as supervisor:
        response = supervisor.get(f"{AUDIT}/platform-audit-events/{platform.json()['id']}")
    assert response.status_code == 200
    assert response.json()["company_id"] is None


def test_operational_context_down_returns_503(admin, company) -> None:
    require_audit()
    subprocess.run(["docker", "stop", "sio-operational-context-service"], check=True, capture_output=True)
    try:
        response = admin.get(f"{AUDIT}/companies/{company}/audit-events")
        assert response.status_code == 503
        assert response.json()["dependency"] == "operational-context"
        # La plataforma y el registro no dependen de Operational Context.
        assert admin.get(f"{AUDIT}/platform-audit-events").status_code == 200
    finally:
        subprocess.run(["docker", "start", "sio-operational-context-service"], check=True, capture_output=True)
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            try:
                if httpx.get(OPERATIONAL_CONTEXT.removesuffix("/api/v1") + "/health/ready", timeout=3).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            time.sleep(1)

    assert admin.get(f"{AUDIT}/companies/{company}/audit-events").status_code == 200
