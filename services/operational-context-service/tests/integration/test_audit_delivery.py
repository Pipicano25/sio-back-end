"""Entrega real de la auditoría de Operational Context (feature 016; SC-007; RC-04; T032).

Exige el entorno integrado con `operational-context-audit-outbox-worker` y Audit en ejecución.
`admin.test` se registra como usuario de la empresa ficticia para poder leer su historial en Audit
(la consulta por empresa exige membresía `ACTIVE`). Datos ficticios de validación.
"""

from __future__ import annotations

import os
import time

import pytest

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

AUDIT = os.environ.get("AUDIT_SERVICE_BASE_URL", "http://127.0.0.1:8110/api/v1").rstrip("/")


def _history(client, company: str, entity_type: str, entity_id: str) -> list[dict]:
    response = client.get(f"{AUDIT}/companies/{company}/entity-history/{entity_type}/{entity_id}", params={"page_size": 100})
    return response.json()["items"] if response.status_code == 200 else []


def _wait(client, company: str, entity_type: str, entity_id: str, actions: list[str], timeout: float = 120) -> list[dict]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        items = _history(client, company, entity_type, entity_id)
        if all(any(item["action"] == action for item in items) for action in actions):
            return items
        time.sleep(2)
    pytest.fail(f"Audit no recibió {actions} de {entity_type} {entity_id}.")


@pytest.fixture(scope="module")
def member(client, company_id, person_id):
    response = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies/{company_id}/application-users", json={
        "username": "admin.test",
        "person_identity_id": person_id,
        "display_name": f"Auditoría {RUN_ID} (dato ficticio)",
    })
    assert response.status_code in (201, 409), response.text
    return response


def test_company_and_branch_history_reaches_audit_once(client, company_id, member, geography) -> None:
    created = client.post(f"{OPERATIONAL_CONTEXT}/api/v1/companies/{company_id}/branches", json={
        "code": f"AUD-{RUN_ID}", "name": "Sucursal de auditoría (dato ficticio)",
        "email": "sede.auditoria@empresa-ficticia.co",
    })
    assert created.status_code == 201, created.text
    branch = created.json()
    body = {key: branch[key] for key in (
        "code", "email", "phone", "address_line", "country_id", "administrative_division_id", "city_id",
        "postal_code", "latitude", "longitude", "timezone", "version",
    )}
    body["name"] = "Sucursal de auditoría renombrada (dato ficticio)"
    updated = client.put(f"{OPERATIONAL_CONTEXT}/api/v1/branches/{branch['id']}", json=body)
    assert updated.status_code == 200, updated.text

    company_events = _wait(client, company_id, "Company", company_id, ["CREATE_COMPANY"])
    branch_events = _wait(client, company_id, "Branch", branch["id"], ["CREATE_BRANCH", "UPDATE_BRANCH"])
    time.sleep(5)

    assert [e["action"] for e in _history(client, company_id, "Company", company_id)].count("CREATE_COMPANY") == 1
    assert {e["source_service"] for e in company_events + branch_events} == {"operational-context-service"}
    history = _history(client, company_id, "Branch", branch["id"])
    assert [e["action"] for e in history] == ["CREATE_BRANCH", "UPDATE_BRANCH"]  # orden por occurred_at
    assert history[0]["new_values"]["email"] == "<registrado>"
    assert "new_values.email" in history[0]["redacted_paths"]
    assert "sede.auditoria@empresa-ficticia.co" not in str(history)
    assert history[1]["new_values"] == {"name": "Sucursal de auditoría renombrada (dato ficticio)"}
    assert history[1]["branch_id"] == branch["id"] and history[1]["keycloak_user_id"]
