"""Reenvío idempotente y rechazo permanente (feature 016; RC-03, RC-04; T070).

- Reenvío tras respuesta perdida: la fila `SENT` vuelve a `PENDING` (como si el worker no hubiera
  recibido la confirmación); el worker la reenvía, Audit responde `ALREADY_EXISTS` y el evento sigue
  una sola vez.
- Rechazo permanente: un evento inválido insertado directamente en la outbox (el emisor nunca lo
  produce: `record_audit_event` valida antes) queda `PENDING` con su error, aparece en los logs con
  su `event_id` y no bloquea a los demás. La fila de prueba se elimina al final (dato de prueba).
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid

import pytest

from tests.integration.test_audit_delivery import _history, member  # noqa: F401
from tests.integration.test_real_dependencies import (  # noqa: F401 (fixtures)
    OPERATIONAL_CONTEXT,
    RUN_ID,
    client,
    company_id,
    geography,
    organization_id,
    person_id,
)

pytestmark = pytest.mark.integration

DB = "sio-operational-context-db"
WORKER = "sio-operational-context-audit-outbox-worker"


def _sql(statement: str) -> str:
    return subprocess.run(
        ["docker", "exec", "-i", DB, "sh", "-c", 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At'],
        input=statement, capture_output=True, text=True, check=True,
    ).stdout.strip()


def _wait(predicate, timeout: float, message: str) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, message
        time.sleep(2)


def _branch(client, company_id: str, suffix: str) -> dict:
    response = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies/{company_id}/branches", json={
        "code": f"RS-{RUN_ID}-{suffix}", "name": "Sucursal de reenvío (dato ficticio)"})
    assert response.status_code == 201, response.text
    return response.json()


def test_resend_after_lost_response_is_not_duplicated(client, company_id, member) -> None:
    branch = _branch(client, company_id, "A")
    _wait(lambda: len(_history(client, company_id, "Branch", branch["id"])) == 1, 120, "sin entrega inicial")
    event_id = _sql(f"SELECT event_id FROM audit_outbox WHERE payload->>'entity_id' = '{branch['id']}'")
    assert _sql(f"SELECT status FROM audit_outbox WHERE event_id = '{event_id}'") == "SENT"

    _sql(f"UPDATE audit_outbox SET status = 'PENDING', sent_at = NULL, next_attempt_at = now() WHERE event_id = '{event_id}'")
    _wait(lambda: _sql(f"SELECT status FROM audit_outbox WHERE event_id = '{event_id}'") == "SENT", 120, "sin reenvío")
    time.sleep(3)

    history = _history(client, company_id, "Branch", branch["id"])
    assert len(history) == 1 and history[0]["event_id"] == event_id  # ALREADY_EXISTS: sin duplicado


def test_rejected_event_does_not_block_the_others(client, company_id, member) -> None:
    valid = _branch(client, company_id, "B")
    _wait(lambda: len(_history(client, company_id, "Branch", valid["id"])) == 1, 120, "sin entrega inicial")
    payload = json.loads(_sql(f"SELECT payload FROM audit_outbox WHERE payload->>'entity_id' = '{valid['id']}'"))
    bad_id = str(uuid.uuid4())
    payload.update({"event_id": bad_id, "action": "accion-invalida", "entity_id": str(uuid.uuid4())})
    literal = json.dumps(payload).replace("'", "''")
    _sql(f"INSERT INTO audit_outbox (event_id, payload) VALUES ('{bad_id}', '{literal}'::jsonb)")
    try:
        _wait(lambda: _sql(f"SELECT attempts FROM audit_outbox WHERE event_id = '{bad_id}'") not in ("", "0"), 60,
              "el evento inválido no se intentó")
        after = _branch(client, company_id, "C")
        _wait(lambda: len(_history(client, company_id, "Branch", after["id"])) == 1, 120,
              "el evento válido quedó bloqueado por el rechazado")

        status, code = _sql(f"SELECT status, coalesce(last_error_code, '') FROM audit_outbox WHERE event_id = '{bad_id}'").split("|")
        assert status == "PENDING" and code
        logs = subprocess.run(["docker", "logs", "--since", "5m", WORKER], capture_output=True, text=True).stdout
        logs += subprocess.run(["docker", "logs", "--since", "5m", WORKER], capture_output=True, text=True).stderr
        assert bad_id in logs
    finally:
        _sql(f"DELETE FROM audit_outbox WHERE event_id = '{bad_id}'")
