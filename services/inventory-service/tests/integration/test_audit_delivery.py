"""Entrega real de la auditoría por el `inventory-audit-outbox-worker` (FR-070 a FR-073; SC-009; T063).

Ejecutar con `pytest -m integration` con audit-service y el worker en marcha. La segunda prueba
detiene `sio-audit-service` durante una salida y lo vuelve a iniciar.
"""

from __future__ import annotations

import subprocess
import time

import httpx
import pytest

from uuid import uuid4

from tests.integration.support import AUDIT, INVENTORY, operation, require_services, user_client

pytestmark = pytest.mark.integration

AUDIT_CONTAINER = "sio-audit-service"
WORKER_CONTAINER = "sio-inventory-audit-outbox-worker"


@pytest.fixture(scope="module", autouse=True)
def audit_running():
    require_services(f"{AUDIT.removesuffix('/api/v1')}/health/ready")


def _events(admin, company: str, entity_id: str, entity_type: str = "InventoryOperation") -> list[dict]:
    response = admin.get(f"{AUDIT}/companies/{company}/audit-events", params={"entity_type": entity_type})
    if response.status_code != 200:
        return []
    return [item for item in response.json()["items"] if item["entity_id"] == entity_id]


def _wait_events(admin, company: str, entity_id: str, timeout: float = 90, entity_type: str = "InventoryOperation") -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        found = _events(admin, company, entity_id, entity_type)
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



def test_adjustment_and_count_completion_reach_audit_once(admin, operator, real_world) -> None:
    """013 (R-11; quickstart 21): `CREATE_INVENTORY_ADJUSTMENT` y `COMPLETE_INVENTORY_COUNT` llegan una vez."""
    product = real_world.products[0]
    assert operator.post(f"{INVENTORY}/inventory-entries", json=operation(real_world, (product, "6"), unit_cost="40")).status_code == 201
    with user_client("inventario.test") as inventario:
        adjustment = inventario.post(
            f"{INVENTORY}/companies/{real_world.company}/inventory-adjustments",
            json={
                "adjustment_key": str(uuid4()),
                "branch_id": real_world.branch,
                "company_product_id": product,
                "adjustment_type": "NEGATIVE",
                "quantity": "1",
                "reason": "Ajuste ficticio de validación INV",
            },
        )
        assert adjustment.status_code == 201, adjustment.text
        base = f"{INVENTORY}/companies/{real_world.company}/inventory-counts"
        count = inventario.post(base, json={"branch_id": real_world.branch}).json()
        started = inventario.post(f"{base}/{count['id']}/start", json={"version": 1}).json()
        inventario.put(f"{base}/{count['id']}/details/{product}", json={"counted_quantity": "0"})
        completed = inventario.post(
            f"{base}/{count['id']}/complete", json={"completion_key": str(uuid4()), "version": started["version"]}
        )
        assert completed.status_code == 200, completed.text

    adjustment_events = _wait_events(
        admin, real_world.company, adjustment.json()["id"], entity_type="InventoryAdjustment"
    )
    count_events = _wait_events(admin, real_world.company, count["id"], entity_type="InventoryCount")
    time.sleep(5)
    assert [event["action"] for event in adjustment_events] == ["CREATE_INVENTORY_ADJUSTMENT"]
    completions = [
        event
        for event in _events(admin, real_world.company, count["id"], "InventoryCount")
        if event["action"] == "COMPLETE_INVENTORY_COUNT"
    ]
    assert len(completions) == 1
    assert completions[0]["new_values"]["operation_id"] == completed.json()["operation_id"]
    assert {event["action"] for event in count_events} <= {"START_INVENTORY_COUNT", "COMPLETE_INVENTORY_COUNT"}
