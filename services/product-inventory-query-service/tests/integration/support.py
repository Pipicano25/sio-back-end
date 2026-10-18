"""Utilidades de integración real de product-inventory-query-service (spec 022, T132).

Solo contra la pila aislada `sio-it-*` (`validation/isolated-stack/`): `SIO_TEST_TARGET=isolated` y
`validation/isolation_guard.py` sobre **todas** las URL, incluido Keycloak, antes de la primera solicitud. Los
secretos se leen de `validation/isolated-stack/.env` (los de esa pila), nunca de `infrastructure/.env`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[4]


def _base(variable: str, default: str) -> str:
    return os.environ.get(variable, default).rstrip("/")


PIQ = _base("PRODUCT_INVENTORY_QUERY_INTEGRATION_BASE_URL", "http://127.0.0.1:18112/api/v1")
OC = _base("OPERATIONAL_CONTEXT_INTEGRATION_BASE_URL", "http://127.0.0.1:18104/api/v1")
CR = _base("COMMERCIAL_RELATIONSHIP_INTEGRATION_BASE_URL", "http://127.0.0.1:18106/api/v1")
PC = _base("PRODUCT_CATALOG_INTEGRATION_BASE_URL", "http://127.0.0.1:18103/api/v1")
INVENTORY = _base("INVENTORY_INTEGRATION_BASE_URL", "http://127.0.0.1:18109/api/v1")
TOKEN_URL = _base("KEYCLOAK_TOKEN_URL", "http://127.0.0.1:18081/realms/sio/protocol/openid-connect/token")
TARGETS = {"product_inventory_query": PIQ, "operational_context": OC, "commercial_relationship": CR,
           "product_catalog": PC, "inventory": INVENTORY, "keycloak": TOKEN_URL}


def isolation_guard():
    spec = importlib.util.spec_from_file_location("sio_isolation_guard", REPO / "validation" / "isolation_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_isolation() -> dict[str, str]:
    return isolation_guard().check_targets(TARGETS)


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
    check_isolation()
    return httpx.Client(timeout=30, auth=Token({
        "grant_type": "password", "client_id": "sio-web", "scope": "openid", "username": username,
        "password": isolated_secret("KEYCLOAK_TEST_USER_PASSWORD")}))


def anonymous_client() -> httpx.Client:
    check_isolation()
    return httpx.Client(timeout=30)


def walk(client: httpx.Client, path: str, params: list[tuple[str, str]], *, limit: int = 300) -> tuple[list, list]:
    items, pages, cursor = [], [], None
    for _ in range(limit):
        response = client.get(f"{PIQ}{path}", params=params + ([("cursor", cursor)] if cursor else []))
        assert response.status_code == 200, response.text
        body = response.json()
        pages.append(body)
        items.extend(body["items"])
        if not body["has_next"]:
            assert body["next_cursor"] is None
            return items, pages
        cursor = body["next_cursor"]
    raise AssertionError("el recorrido no terminó")


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=True, timeout=120).stdout


def container_logs(container: str, since: str = "60m") -> str:
    """Salida estándar **y** de error del contenedor aislado (los logs de Python van a la de error)."""
    isolation_guard().check_container(container)
    completed = subprocess.run(["docker", "logs", "--since", since, container], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, check=True, timeout=120)
    return completed.stdout


def stop_and_restore(container: str):
    """Detiene un contenedor **aislado** (la barrera lo comprueba) y devuelve la función que lo restaura."""
    isolation_guard().check_container(container)
    docker("stop", container)

    def restore() -> None:
        isolation_guard().check_container(container)
        docker("start", container)
        for _ in range(90):
            if docker("inspect", "-f", "{{.State.Health.Status}}", container).strip() == "healthy":
                return
            time.sleep(2)
        raise AssertionError(f"{container} no volvió a estar sano")

    return restore
