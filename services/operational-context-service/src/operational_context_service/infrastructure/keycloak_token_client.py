"""Token técnico `client_credentials` del cliente propio del servicio (D5, DS-14).

Solo lo usa el adaptador de la Admin API de Keycloak (lectura de cuentas y de
roles efectivos). No valida tokens (eso sigue en `sio-auth`, Principio V) y
nunca registra ni expone el token ni el secreto (Principio IX). No reutiliza
código de otros microservicios (Principio I).
"""

from __future__ import annotations

import logging
import threading
import time

import httpx

from operational_context_service.application.exceptions import (
    KEYCLOAK_TOKEN_REJECTED,
    DependencyUnavailableError,
)
from operational_context_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

PROVIDER = "keycloak"
# El token se renueva cuando le quedan menos de estos segundos de vida.
REFRESH_MARGIN_SECONDS = 30


class KeycloakTokenClient:
    """Obtiene y reutiliza en memoria el token técnico hasta 30 s antes de expirar."""

    def __init__(
        self,
        *,
        base_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
        clock=time.monotonic,
    ) -> None:
        self._token_url = f"{base_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._clock = clock
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at = 0.0

    def __repr__(self) -> str:  # nunca muestra el secreto ni el token
        return f"KeycloakTokenClient(client_id={self._client_id!r})"

    def get_token(self) -> str:
        """Devuelve un token vigente, pidiéndolo si hace falta.

        Raises:
            DependencyUnavailableError: Si Keycloak no entrega el token.
        """
        with self._lock:
            if self._token is not None and self._clock() < self._expires_at - REFRESH_MARGIN_SECONDS:
                return self._token

            self._token, lifetime = self._request_token()
            self._expires_at = self._clock() + lifetime

            return self._token

    def invalidate(self) -> None:
        """Descarta el token en memoria (p. ej. tras un `401` de la Admin API)."""
        with self._lock:
            self._token = None
            self._expires_at = 0.0

    def _request_token(self) -> tuple[str, float]:
        try:
            with httpx.Client(timeout=self._timeout_seconds, transport=self._transport) as client:
                response = client.post(
                    self._token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                    },
                )
        except httpx.HTTPError as exc:
            raise self._rejected(type(exc).__name__) from None

        if response.status_code != 200:
            raise self._rejected(f"estado={response.status_code}")

        try:
            body = response.json()
        except ValueError:
            body = None

        token = body.get("access_token") if isinstance(body, dict) else None
        lifetime = body.get("expires_in", 60) if isinstance(body, dict) else 60

        if not isinstance(token, str) or not token:
            raise self._rejected("cuerpo_inesperado")

        try:
            lifetime = float(lifetime)
        except (TypeError, ValueError):
            lifetime = 60.0

        return token, lifetime

    def _rejected(self, outcome: str) -> DependencyUnavailableError:
        logger.error(
            "No fue posible obtener el token técnico causa=%s proveedor=%s cliente=%s resultado=%s",
            KEYCLOAK_TOKEN_REJECTED,
            PROVIDER,
            self._client_id,
            outcome,
        )
        return DependencyUnavailableError(
            provider=PROVIDER,
            cause=KEYCLOAK_TOKEN_REJECTED,
            operation="client_credentials_token",
        )
