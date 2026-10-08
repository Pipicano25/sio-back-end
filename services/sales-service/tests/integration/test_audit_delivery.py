"""Entrega real de la auditoría por `sales-audit-outbox-worker` (FR-031; SC-007; DS-12; T082).

La segunda prueba detiene `sio-audit-service` durante una confirmación y lo vuelve a iniciar.
"""

from __future__ import annotations

import time

import httpx
import pytest

from tests.integration.support import AUDIT, SALES, docker, draft_body, new_key, wait_until

pytestmark = pytest.mark.integration

AUDIT_CONTAINER = "sio-audit-service"


@pytest.fixture(scope="module", autouse=True)
def audit_running():
    try:
        httpx.get(f"{AUDIT.removesuffix('/api/v1')}/health/ready", timeout=5).raise_for_status()
    except httpx.HTTPError:
        pytest.skip("audit-service no disponible.")


def events(admin, company: str, entity_id: str) -> list[dict]:
    response = admin.get(f"{AUDIT}/companies/{company}/audit-events", params={"entity_type": "Sale"})
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
    return {"company_product_id": world.product_2.company_product, "quantity": "1"}


def test_confirmation_and_cancellation_reach_audit_once(admin, seller, real_world, sequence) -> None:
    base = f"{SALES}/companies/{real_world.company}/sales"
    draft = seller.post(base, json=draft_body(real_world, line(real_world))).json()
    confirmed = seller.post(f"{base}/{draft['id']}/confirmation", json={"version": 1}, headers={"Idempotency-Key": new_key()}).json()
    seller.post(
        f"{base}/{draft['id']}/cancellation",
        json={"version": confirmed["version"], "reason": "Anulación ficticia de validación"},
        headers={"Idempotency-Key": new_key()},
    )
    confirm_event = wait_events(admin, real_world.company, draft["id"], "CONFIRM_SALE")
    cancel_event = wait_events(admin, real_world.company, draft["id"], "CANCEL_SALE")
    time.sleep(5)
    assert len([e for e in events(admin, real_world.company, draft["id"]) if e["action"] == "CONFIRM_SALE"]) == 1
    assert confirm_event[0]["source_service"] == "sales-service"
    assert confirm_event[0]["new_values"]["number"] == confirmed["number"]
    assert confirm_event[0]["new_values"]["inventory_operation_id"] == confirmed["inventory_operation_id"]
    assert cancel_event[0]["reason"] == "Anulación ficticia de validación"
    for word in ("unit_cost", "cost_total", "cost_known", "gross_margin", "has_unknown_cost"):  # DS-12
        assert word not in str(confirm_event[0]) and word not in str(cancel_event[0])


def test_audit_down_does_not_block_confirmation(admin, seller, real_world, sequence) -> None:
    base = f"{SALES}/companies/{real_world.company}/sales"
    draft = seller.post(base, json=draft_body(real_world, line(real_world))).json()
    docker("stop", AUDIT_CONTAINER)
    try:
        response = seller.post(f"{base}/{draft['id']}/confirmation", json={"version": 1}, headers={"Idempotency-Key": new_key()})
        assert response.status_code == 200, response.text
        time.sleep(6)
    finally:
        docker("start", AUDIT_CONTAINER)
    wait_until(lambda: httpx.get(f"{AUDIT.removesuffix('/api/v1')}/health/ready", timeout=5).status_code == 200, 90, "Audit no volvió")
    wait_events(admin, real_world.company, draft["id"], "CONFIRM_SALE", timeout=360)
    time.sleep(5)
    assert len([e for e in events(admin, real_world.company, draft["id"]) if e["action"] == "CONFIRM_SALE"]) == 1
