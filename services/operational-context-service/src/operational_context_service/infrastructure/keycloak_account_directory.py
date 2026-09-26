"""Adaptador de solo lectura de la Admin API de Keycloak (R-06, R-07, DS-14).

Única implementación productiva del puerto `IdentityAccountDirectory`, usada en
todos los entornos (sin modos). Solo lee: la cuenta de servicio del cliente
`operational-context-service` tiene `view-users` y `query-clients`. De cada
cuenta solo se persiste el `sub` (FR-065). Contrato:
`specs/005-operational-context-users/contracts/keycloak-dependency.md`.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any
from urllib.parse import quote

import httpx

from operational_context_service.application.exceptions import (
    KEYCLOAK_ADMIN_DENIED,
    KEYCLOAK_AMBIGUOUS_USERNAME,
    KEYCLOAK_UNREACHABLE,
    DependencyUnavailableError,
)
from operational_context_service.application.ports import AccountRef
from operational_context_service.infrastructure.keycloak_token_client import KeycloakTokenClient
from operational_context_service.observability import (
    SERVICE_LOGGER,
    build_traceparent,
    current_trace_id,
)

logger = logging.getLogger(SERVICE_LOGGER)

PROVIDER = "keycloak"
# Keycloak nombra las cuentas de servicio `service-account-<clientId>`. La Admin API de
# Keycloak 26 no devuelve `serviceAccountClientId` en la representación del usuario
# (verificado en la validación de T091), así que el prefijo reservado es la señal fiable.
SERVICE_ACCOUNT_PREFIX = "service-account-"


def _is_service_account(body: dict[str, Any], username: str) -> bool:
    """Cuenta técnica de un cliente `client_credentials` (FR-019)."""
    return bool(body.get("serviceAccountClientId")) or username.lower().startswith(SERVICE_ACCOUNT_PREFIX)


class KeycloakAccountDirectory:
    """Consulta cuentas y roles efectivos con la identidad técnica del servicio."""

    def __init__(
        self,
        *,
        base_url: str,
        realm: str,
        sio_api_client_id: str,
        timeout_seconds: float,
        token_client: KeycloakTokenClient,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._admin_url = f"{base_url.rstrip('/')}/admin/realms/{realm}"
        self._sio_api_client_id = sio_api_client_id
        self._timeout_seconds = timeout_seconds
        self._token_client = token_client
        self._transport = transport
        self._client_uuid: str | None = None
        self._client_uuid_lock = threading.Lock()

    # ------------------------------------------------------------------ puerto

    def get_account(self, sub: str) -> AccountRef | None:
        body = self._get("get_account", f"/users/{quote(sub, safe='')}")

        if body is None:
            return None

        return self._account("get_account", body)

    def find_account_by_username(self, username: str) -> AccountRef | None:
        operation = "find_account_by_username"
        normalized = username.strip().lower()
        body = self._get(
            operation,
            "/users",
            params={"username": normalized, "exact": "true"},
        )

        if body is None:
            return None

        if not isinstance(body, list):
            raise self._unavailable(operation, KEYCLOAK_UNREACHABLE, "cuerpo_inesperado")

        matches = [item for item in body if isinstance(item, dict)]

        if not matches:
            return None

        if len(matches) > 1:
            raise self._unavailable(operation, KEYCLOAK_AMBIGUOUS_USERNAME, f"coincidencias={len(matches)}")

        return self._account(operation, matches[0])

    def get_permission_roles(self, sub: str) -> frozenset[str]:
        operation = "get_permission_roles"
        client_uuid = self._resolve_client_uuid(sub)

        if client_uuid is None:
            # Ni la cuenta ni sus grupos tienen roles de `sio-api`: no hay permisos SIO.
            return frozenset()

        body = self._get(
            operation,
            f"/users/{quote(sub, safe='')}/role-mappings/clients/{client_uuid}/composite",
        )

        # Cuenta inexistente → sin roles: la evaluación del permiso lo niega.
        if body is None:
            return frozenset()

        if not isinstance(body, list):
            raise self._unavailable(operation, KEYCLOAK_UNREACHABLE, "cuerpo_inesperado")

        return frozenset(
            item["name"]
            for item in body
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        )

    # ------------------------------------------------------------------ apoyo

    def _resolve_client_uuid(self, sub: str) -> str | None:
        """UUID interno del cliente `sio-api`, conservado en memoria del proceso.

        Con `query-clients`, Keycloak 26 devuelve la lista de clientes vacía si la
        cuenta no tiene además `view-clients` (hallazgo de T091). Para no pedir más
        privilegios, el UUID se toma entonces de las asignaciones de roles de la
        cuenta o de sus grupos (legibles con `view-users`), que incluyen el `id` del
        cliente. `None` si la cuenta no tiene ningún rol de `sio-api`.
        """
        with self._client_uuid_lock:
            if self._client_uuid is not None:
                return self._client_uuid

            operation = "resolve_sio_api_client"
            body = self._get(operation, "/clients", params={"clientId": self._sio_api_client_id})
            clients = [item for item in body if isinstance(item, dict)] if isinstance(body, list) else []

            if len(clients) == 1 and isinstance(clients[0].get("id"), str):
                self._client_uuid = clients[0]["id"]
                return self._client_uuid

            # Solo se conserva un UUID encontrado: otra cuenta sí puede tener roles de `sio-api`.
            self._client_uuid = self._client_uuid_from_mappings(operation, sub)

            return self._client_uuid

    def _client_uuid_from_mappings(self, operation: str, sub: str) -> str | None:
        user_path = f"/users/{quote(sub, safe='')}"
        sources = [self._get(operation, f"{user_path}/role-mappings")]
        groups = self._get(operation, f"{user_path}/groups") or []

        if not isinstance(groups, list):
            raise self._unavailable(operation, KEYCLOAK_UNREACHABLE, "cuerpo_inesperado")

        sources += [
            self._get(operation, f"/groups/{group['id']}/role-mappings")
            for group in groups
            if isinstance(group, dict) and isinstance(group.get("id"), str)
        ]

        for mappings in sources:
            client_mappings = (mappings or {}).get("clientMappings") if isinstance(mappings, dict) else None
            entry = (client_mappings or {}).get(self._sio_api_client_id)

            if isinstance(entry, dict) and isinstance(entry.get("id"), str):
                return entry["id"]

        return None

    def _account(self, operation: str, body: dict[str, Any]) -> AccountRef:
        sub = body.get("id")
        username = body.get("username")
        enabled = body.get("enabled")

        if not isinstance(sub, str) or not sub or not isinstance(username, str) or not isinstance(enabled, bool):
            raise self._unavailable(operation, KEYCLOAK_UNREACHABLE, "cuerpo_inesperado")

        return AccountRef(
            sub=sub,
            username=username,
            enabled=enabled,
            is_service_account=_is_service_account(body, username),
        )

    def _get(
        self,
        operation: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        retry_on_unauthorized: bool = True,
    ) -> Any:
        """GET a la Admin API: cuerpo JSON en `200`, `None` en `404`."""
        token = self._token_client.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        trace_id = current_trace_id()

        if trace_id:
            headers["traceparent"] = build_traceparent(trace_id)

        started = time.perf_counter()

        try:
            with httpx.Client(timeout=self._timeout_seconds, transport=self._transport) as client:
                response = client.get(f"{self._admin_url}{path}", headers=headers, params=params)
        except httpx.HTTPError as exc:
            raise self._unavailable(operation, KEYCLOAK_UNREACHABLE, type(exc).__name__, started) from None

        if response.status_code == 404:
            return None

        if response.status_code == 401 and retry_on_unauthorized:
            # Token revocado o expirado antes de lo previsto: se pide uno nuevo una vez.
            self._token_client.invalidate()
            return self._get(operation, path, params=params, retry_on_unauthorized=False)

        if response.status_code in {401, 403}:
            raise self._unavailable(
                operation,
                KEYCLOAK_ADMIN_DENIED,
                f"estado={response.status_code}",
                started,
                level=logging.WARNING,
            )

        if response.status_code != 200:
            raise self._unavailable(operation, KEYCLOAK_UNREACHABLE, f"estado={response.status_code}", started)

        try:
            return response.json()
        except ValueError:
            raise self._unavailable(operation, KEYCLOAK_UNREACHABLE, "cuerpo_inesperado", started) from None

    def _unavailable(
        self,
        operation: str,
        cause: str,
        outcome: str,
        started: float | None = None,
        *,
        level: int = logging.ERROR,
    ) -> DependencyUnavailableError:
        duration_ms = None if started is None else round((time.perf_counter() - started) * 1000)
        logger.log(
            level,
            "No fue posible consultar la dependencia causa=%s proveedor=%s operacion=%s "
            "resultado=%s duracion_ms=%s",
            cause,
            PROVIDER,
            operation,
            outcome,
            duration_ms,
        )
        return DependencyUnavailableError(provider=PROVIDER, cause=cause, operation=operation)
