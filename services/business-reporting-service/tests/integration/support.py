"""Integración real de business-reporting-service, **solo** en la pila aislada `sio-it-*` (spec 023).

`SIO_TEST_TARGET=isolated` y `validation/isolation_guard.py` sobre **todas** las URL, incluido Keycloak, antes de la
primera solicitud. Los secretos se leen de `validation/isolated-stack/.env`, nunca de `infrastructure/.env`.
Si el contenedor `sio-it-business-reporting-service` todavía no existe (no se ha autorizado agregarlo), las pruebas
se **omiten** con el motivo: nunca se dan por aprobadas sin ejecutarse.
"""

from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[4]


def _base(variable: str, default: str) -> str:
    return os.environ.get(variable, default).rstrip("/")


BRS = _base("BUSINESS_REPORTING_INTEGRATION_BASE_URL", "http://127.0.0.1:18113/api/v1")
OC = _base("OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL", "http://127.0.0.1:18104/api/v1")
SALES = _base("SALES_INTEGRATION_BASE_URL", "http://127.0.0.1:18108/api/v1")
PURCHASE = _base("PURCHASE_INTEGRATION_BASE_URL", "http://127.0.0.1:18107/api/v1")
INVENTORY = _base("INVENTORY_INTEGRATION_BASE_URL", "http://127.0.0.1:18109/api/v1")
TOKEN_URL = _base("KEYCLOAK_TOKEN_URL", "http://127.0.0.1:18081/realms/sio/protocol/openid-connect/token")
TARGETS = {"business_reporting": BRS, "operational_context": OC, "sales": SALES, "purchase": PURCHASE,
           "inventory": INVENTORY, "keycloak": TOKEN_URL}


def isolation_guard():
    spec = importlib.util.spec_from_file_location("sio_isolation_guard", REPO / "validation" / "isolation_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def isolated_secret(name: str) -> str:
    path = Path(os.environ.get("SIO_IT_ENV_FILE", REPO / "validation" / "isolated-stack" / ".env"))
    for line in path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == name:
            return value.strip()
    raise RuntimeError(f"{name} no está en el .env de la pila aislada")


def manifest() -> dict:
    path = Path(os.environ.get("SIO_IT_STATE_DIR", "/tmp/sio-it-state")) / "seed.json"
    return json.loads(path.read_text(encoding="utf-8"))


class Token(httpx.Auth):
    def __init__(self, data: dict) -> None:
        self._data, self._token, self._expires = data, None, 0.0

    def auth_flow(self, request):
        if self._token is None or time.monotonic() > self._expires - 30:
            body = httpx.post(TOKEN_URL, data=self._data, timeout=20).raise_for_status().json()
            self._token, self._expires = body["access_token"], time.monotonic() + float(body.get("expires_in", 300))
        request.headers["Authorization"] = f"Bearer {self._token}"
        yield request


def user_client(username: str) -> httpx.Client:
    return httpx.Client(timeout=60, auth=Token({
        "grant_type": "password", "client_id": "sio-web", "scope": "openid", "username": username,
        "password": isolated_secret("KEYCLOAK_TEST_USER_PASSWORD")}))
