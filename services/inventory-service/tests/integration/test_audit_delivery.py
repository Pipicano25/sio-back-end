"""Entrega real de la auditoría por el `inventory-audit-outbox-worker` (FR-070 a FR-073; SC-009; T063).

Ejecutar con `pytest -m integration` con audit-service y el worker en marcha. La segunda prueba
detiene `sio-audit-service` durante una salida y lo vuelve a iniciar.
"""

from __future__ import annotations

import subprocess
import time

import httpx
import pytest

from tests.integration.support import AUDIT, INVENTORY, operation, require_services

pytestmark = pytest.mark.integration

AUDIT_CONTAINER = "sio-audit-service"
WORKER_CONTAINER = "sio-inventory-audit-outbox-worker"


@pytest.fixture(scope="module", autouse=True)
def audit_running():
    require_services(f"{AUDIT.removesuffix('/api/v1')}/health/ready")


def _events(admin, company: str, entity_id: str) -> list[dict]:
    response = admin.get(f"{AUDIT}/companies/{company}/audit-events", params={"entity_type": "InventoryOperation"})
    if response.status_code != 200:
        return []
    return [item for item in response.json()["items"] if item["entity_id"] == entity_id]


def _wait_events(admin, company: str, entity_id: str, timeout: float = 90) -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = _events(admin, company, entity_id)
        if found:
            return found
        time.sleep(2)
    pytest.fail(f"El evento de la operación {entity_id} no llegó a Audit.")


def test_applied_operation_reaches_audit(admin, operator, real_world) -> None:
    entry = operator.post(f"{INVENTORY}/inventory-entries", json=operation(real_world, (real_world.products[0], "5")))
    assert entry.status_code == 201, entry.text

    events = _wait_events(admin, real_world.company, entry.json()["id"])
    assert len(events) == 1
    event = events[0]
    assert event["action"] == "APPLY_INVENTORY_ENTRY"
    assert event["source_service"] == "inventory-service"
    assert event["branch_id"] == real_world.branch
    assert event["application_user_id"] == real_world.user
    assert event["new_values"]["lines"][0]["movement_id"] == entry.json()["movements"][0]["id"]


def test_audit_down_does_not_block_and_event_arrives_once(admin, operator, real_world) -> None:
    operator.post(f"{INVENTORY}/inventory-entries", json=operation(real_world, (real_world.products[1], "3")))
    subprocess.run(["docker", "stop", AUDIT_CONTAINER], check=True, capture_output=True)
    try:
        output = operator.post(f"{INVENTORY}/inventory-outputs", json=operation(real_world, (real_world.products[1], "1"), origin_type="SALE"))
        assert output.status_code == 201, output.text
        time.sleep(6)  # el worker intenta, falla y reprograma con backoff
    finally:
        subprocess.run(["docker", "start", AUDIT_CONTAINER], check=True, capture_output=True)

    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{AUDIT.removesuffix('/api/v1')}/health/ready", timeout=5).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(2)

    events = _wait_events(admin, real_world.company, output.json()["id"], timeout=360)
    time.sleep(5)
    assert len(_events(admin, real_world.company, output.json()["id"])) == 1
    assert events[0]["action"] == "APPLY_INVENTORY_OUTPUT"
