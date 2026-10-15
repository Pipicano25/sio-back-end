"""Entrega real de la auditoría por `purchase-audit-outbox-worker` (FR-044; SC-007; T076).

La segunda prueba detiene el Audit aislado durante una confirmación y lo vuelve a iniciar.
Solo actúa sobre contenedores aislados (`support.container`: prefijo `SIO_INTEGRATION_CONTAINER_PREFIX` y
etiqueta `sio.integration.isolated=true`); ante un contenedor persistente la prueba se omite.
"""

from __future__ import annotations

import time

import httpx
import pytest

from tests.integration.support import AUDIT, PURCHASE, container, docker, draft_body, new_key, unit_line, wait_until

pytestmark = pytest.mark.integration



@pytest.fixture(scope="module", autouse=True)
def audit_running():
    try:
        httpx.get(f"{AUDIT.removesuffix('/api/v1')}/health/ready", timeout=5).raise_for_status()
    except httpx.HTTPError:
        pytest.skip("audit-service no disponible.")


def events(admin, company: str, entity_id: str) -> list[dict]:
    response = admin.get(f"{AUDIT}/companies/{company}/audit-events", params={"entity_type": "Purchase"})
    if response.status_code != 200:
        return []
    return [item for item in response.json()["items"] if item["entity_id"] == entity_id]


def wait_events(admin, company: str, entity_id: str, action: str, timeout: float = 120) -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = [event for event in events(admin, company, entity_id) if event["action"] == action]
        if found:
            return found
        time.sleep(2)
    pytest.fail(f"El evento {action} de {entity_id} no llegó a Audit.")


def line(world) -> dict:
    return unit_line(world.product_2, "1", "600")


def test_confirmation_and_cancellation_reach_audit_once(admin, buyer, real_world, sequence) -> None:
    base = f"{PURCHASE}/companies/{real_world.company}/purchases"
    draft = buyer.post(base, json=draft_body(real_world, line(real_world))).json()
    confirmed = buyer.post(f"{base}/{draft['id']}/confirmation", json={"version": 1}, headers={"Idempotency-Key": new_key()}).json()
    received = buyer.post(  # spec 020: la recepción aplica la entrada en Inventory
        f"{base}/{draft['id']}/receipt",
        json={"version": confirmed["version"], "full_receipt_confirmed": True},
        headers={"Idempotency-Key": new_key()},
    ).json()
    buyer.post(
        f"{base}/{draft['id']}/cancellation",
        json={"version": received["version"], "reason": "Anulación ficticia de validación"},
        headers={"Idempotency-Key": new_key()},
    )
    confirm_event = wait_events(admin, real_world.company, draft["id"], "CONFIRM_PURCHASE")
    cancel_event = wait_events(admin, real_world.company, draft["id"], "CANCEL_PURCHASE")
    time.sleep(5)
    assert len([e for e in events(admin, real_world.company, draft["id"]) if e["action"] == "CONFIRM_PURCHASE"]) == 1
    assert confirm_event[0]["source_service"] == "purchase-service"
    assert confirm_event[0]["new_values"]["number"] == confirmed["number"]
    assert confirm_event[0]["new_values"]["receipt_status"] == "PENDING"
    receive_event = wait_events(admin, real_world.company, draft["id"], "RECEIVE_PURCHASE")
    assert receive_event[0]["new_values"]["inventory_operation_id"] == received["inventory_operation_id"]
    assert cancel_event[0]["reason"] == "Anulación ficticia de validación"


def test_audit_down_does_not_block_confirmation(admin, buyer, real_world, sequence) -> None:
    audit_container = container("sio-audit-service")
    base = f"{PURCHASE}/companies/{real_world.company}/purchases"
    draft = buyer.post(base, json=draft_body(real_world, line(real_world))).json()
    docker("stop", audit_container)
    try:
        response = buyer.post(f"{base}/{draft['id']}/confirmation", json={"version": 1}, headers={"Idempotency-Key": new_key()})
        assert response.status_code == 200, response.text
        time.sleep(6)
    finally:
        docker("start", audit_container)
    wait_until(lambda: httpx.get(f"{AUDIT.removesuffix('/api/v1')}/health/ready", timeout=5).status_code == 200, 90, "Audit no volvió")
    wait_events(admin, real_world.company, draft["id"], "CONFIRM_PURCHASE", timeout=360)
    time.sleep(5)
    assert len([e for e in events(admin, real_world.company, draft["id"]) if e["action"] == "CONFIRM_PURCHASE"]) == 1
