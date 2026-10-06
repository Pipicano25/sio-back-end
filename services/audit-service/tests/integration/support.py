"""Utilidades de las pruebas de integración (entorno integrado; secretos solo por entorno o `.env`)."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import httpx
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AUDIT = os.environ.get("AUDIT_INTEGRATION_BASE_URL", "http://localhost:8110/api/v1").rstrip("/")
AUDIT_ROOT = AUDIT.removesuffix("/api/v1")
OPERATIONAL_CONTEXT = os.environ.get(
    "OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL", "http://localhost:8104/api/v1"
).rstrip("/")
TOKEN_URL = os.environ.get("KEYCLOAK_TOKEN_URL", "http://localhost:8081/realms/sio/protocol/openid-connect/token")
EMITTER = os.environ.get("AUDIT_TEST_EMITTER_CLIENT_ID", "audit-test-emitter")


def secret(variable: str) -> str | None:
    value = os.environ.get(variable, "").strip()
    env_file = REPO_ROOT / "infrastructure" / ".env"
    if not value and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            name, separator, content = line.partition("=")
            if separator and name.strip() == variable:
                value = content.strip()
    return value or None


def user_client(username: str) -> httpx.Client:
    password = secret("KEYCLOAK_TEST_USER_PASSWORD")
    if not password:
        pytest.skip("Defina KEYCLOAK_TEST_USER_PASSWORD (o infrastructure/.env).")
    token = httpx.post(
        TOKEN_URL,
        data={"grant_type": "password", "client_id": "sio-web", "scope": "openid",
              "username": username, "password": password},
        timeout=15,
    ).raise_for_status().json()["access_token"]
    return httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=30)


def emitter_client() -> httpx.Client:
    client_secret = secret("AUDIT_TEST_EMITTER_CLIENT_SECRET")
    if not client_secret:
        pytest.skip("Defina AUDIT_TEST_EMITTER_CLIENT_SECRET (o infrastructure/.env).")
    token = httpx.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "client_id": EMITTER, "client_secret": client_secret},
        timeout=15,
    ).raise_for_status().json()["access_token"]
    return httpx.Client(headers={"Authorization": f"Bearer {token}"}, timeout=30)


def require_audit() -> None:
    try:
        httpx.get(f"{AUDIT_ROOT}/health/ready", timeout=5).raise_for_status()
    except httpx.HTTPError:
        pytest.skip("audit-service no está en ejecución en el entorno integrado.")


def admin_member_company(admin: httpx.Client) -> UUID:
    body = admin.get(f"{OPERATIONAL_CONTEXT}/me/operational-context").raise_for_status().json()
    for membership in body["memberships"]:
        if membership["status"] == "ACTIVE" and membership["company_status"] == "ACTIVE":
            return UUID(membership["company_id"])
    pytest.skip("admin.test no tiene membresías ACTIVE en Operational Context.")
