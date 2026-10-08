"""Entrega real de la auditoría de Party Identity (feature 016; SC-007; DS-06; RC-04; T053).

Exige el entorno integrado con `party-identity-audit-outbox-worker` y Audit en ejecución. Eventos de
plataforma: se consultan con `platform-entity-history` (`admin.test` tiene `perm:all:all:all`).
Datos ficticios de validación con un número que cumple la regla vigente.
"""

from __future__ import annotations

import os
import random
import re
import secrets
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[4]
PARTY_IDENTITY = os.environ.get("PARTY_IDENTITY_AUDIT_BASE_URL", "http://127.0.0.1:8101/api/v1").rstrip("/")
GEOGRAPHY = os.environ.get("GEOGRAPHY_AUDIT_BASE_URL", "http://127.0.0.1:8102").rstrip("/")
AUDIT = os.environ.get("AUDIT_SERVICE_BASE_URL", "http://127.0.0.1:8110/api/v1").rstrip("/")
TOKEN_URL = "http://127.0.0.1:8081/realms/sio/protocol/openid-connect/token"
RUN_ID = secrets.token_hex(4).upper()


def _password() -> str | None:
    value = os.environ.get("KEYCLOAK_TEST_USER_PASSWORD", "").strip()
    env_file = REPO_ROOT / "infrastructure" / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, _, content = line.partition("=")
            if name.strip() == "KEYCLOAK_TEST_USER_PASSWORD":
                value = content.strip()
    return value or None


@pytest.fixture(scope="module")
def client():
    password = _password()
    if not password:
        pytest.skip("Defina KEYCLOAK_TEST_USER_PASSWORD (o infrastructure/.env).")
    with httpx.Client(timeout=15) as http:
        token = http.post(TOKEN_URL, data={"grant_type": "password", "client_id": "sio-web", "scope": "openid",
                                           "username": "admin.test", "password": password}).json()["access_token"]
        http.headers["Authorization"] = f"Bearer {token}"
        yield http


def _number(pattern: str) -> str:
    regex = re.compile(pattern)
    for _ in range(500):
        base = str(random.randint(1, 9)) + "".join(random.choice("0123456789") for _ in range(random.randint(7, 9)))
        for candidate in (f"{base}-{random.randint(0, 9)}", base):
            if regex.fullmatch(candidate):
                return candidate
    pytest.skip(f"No se pudo generar un número para {pattern!r}.")


def _history(client, entity_type: str, entity_id: str) -> list[dict]:
    response = client.get(f"{AUDIT}/platform-entity-history/{entity_type}/{entity_id}", params={"page_size": 100})
    return response.json()["items"] if response.status_code == 200 else []


def test_organization_history_reaches_audit_with_protected_identification(client) -> None:
    colombia = client.get(f"{GEOGRAPHY}/global-countries", params={"iso3_code": "COL"}).json()["items"][0]["id"]
    rules = client.get(f"{PARTY_IDENTITY}/identification-type-rules", params={
        "party_kind": "ORGANIZATION", "country_id": colombia, "sigla": "NIT", "is_active": "true"}).json()["items"]
    if not rules:
        pytest.skip("Sin regla NIT activa.")
    number = _number(rules[0]["number_pattern"])
    created = client.post(f"{PARTY_IDENTITY}/organization-identities", json={
        "country_id": colombia, "identification_type": "NIT", "identification_number": number,
        "legal_name": f"PRUEBA SIO AUDITORIA PI {RUN_ID} (DATO FICTICIO DE VALIDACION)",
    })
    assert created.status_code == 201, created.text
    organization = created.json()
    body = {key: organization[key] for key in ("country_id", "identification_type", "identification_number", "legal_name", "version")}
    for optional in ("trade_name", "verification_status"):
        if optional in organization:
            body[optional] = organization[optional]
    renamed = client.put(f"{PARTY_IDENTITY}/organization-identities/{organization['id']}",
                         json={**body, "legal_name": f"PRUEBA SIO AUDITORIA PI {RUN_ID} RENOMBRADA (DATO FICTICIO)"})
    assert renamed.status_code == 200, renamed.text

    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and len(_history(client, "OrganizationIdentity", organization["id"])) < 2:
        time.sleep(2)
    time.sleep(5)
    history = _history(client, "OrganizationIdentity", organization["id"])

    assert [e["action"] for e in history] == ["CREATE_ORGANIZATION_IDENTITY", "UPDATE_ORGANIZATION_IDENTITY"]
    assert {e["source_service"] for e in history} == {"party-identity-service"}
    assert {e["company_id"] for e in history} == {None}
    assert history[0]["new_values"]["identification_number"] == "<registrado>"
    assert "new_values.identification_number" in history[0]["redacted_paths"]
    assert number not in str(history)
    assert history[1]["new_values"] == {"legal_name": f"PRUEBA SIO AUDITORIA PI {RUN_ID} RENOMBRADA (DATO FICTICIO)"}
