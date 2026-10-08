"""Entrega real de la auditoría de Product Catalog (feature 016; SC-007; RC-04; T065).

Exige el entorno integrado con `product-catalog-audit-outbox-worker` (cliente `product-catalog-service`)
y Audit en ejecución. Eventos de plataforma. El primer uso con identidad técnica se valida en la
prueba de entrega de Commercial Relationship. Datos ficticios de validación.
"""

from __future__ import annotations

import os
import secrets
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[4]
PRODUCT_CATALOG = os.environ.get("PRODUCT_CATALOG_AUDIT_BASE_URL", "http://127.0.0.1:8103/api/v1").rstrip("/")
AUDIT = os.environ.get("AUDIT_SERVICE_BASE_URL", "http://127.0.0.1:8110/api/v1").rstrip("/")
TOKEN_URL = "http://127.0.0.1:8081/realms/sio/protocol/openid-connect/token"
RUN_ID = secrets.token_hex(3).upper()


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


def _history(client, entity_type: str, entity_id: str) -> list[dict]:
    response = client.get(f"{AUDIT}/platform-entity-history/{entity_type}/{entity_id}", params={"page_size": 100})
    return response.json()["items"] if response.status_code == 200 else []


def test_brand_history_reaches_audit_once(client) -> None:
    created = client.post(f"{PRODUCT_CATALOG}/brands", json={"code": f"AUD{RUN_ID}", "name": f"Marca ficticia {RUN_ID}"})
    assert created.status_code == 201, created.text
    brand = created.json()
    renamed = client.put(f"{PRODUCT_CATALOG}/brands/{brand['id']}",
                         json={"name": f"Marca ficticia {RUN_ID} renombrada", "description": None, "version": brand["version"]})
    assert renamed.status_code == 200, renamed.text
    deactivated = client.post(f"{PRODUCT_CATALOG}/brands/{brand['id']}/deactivate", json={"version": renamed.json()["version"]})
    assert deactivated.status_code == 200, deactivated.text

    deadline = time.monotonic() + 120
    while time.monotonic() < deadline and len(_history(client, "Brand", brand["id"])) < 3:
        time.sleep(2)
    time.sleep(5)
    history = _history(client, "Brand", brand["id"])

    assert [e["action"] for e in history] == ["CREATE_BRAND", "UPDATE_BRAND", "DEACTIVATE_BRAND"]
    assert {e["source_service"] for e in history} == {"product-catalog-service"}
    assert {e["company_id"] for e in history} == {None}
    assert history[1]["new_values"] == {"name": f"Marca ficticia {RUN_ID} renombrada"}
