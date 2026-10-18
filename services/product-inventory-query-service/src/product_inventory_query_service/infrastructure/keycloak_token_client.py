"""Token técnico por `client_credentials` (D5; research R-03).

El token se guarda en memoria y se renueva 60 s antes de vencer; varias solicitudes concurrentes comparten una
sola renovación. El secreto y el token nunca se registran.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable

import httpx

from product_inventory_query_service.application.exceptions import KEYCLOAK, DependencyUnavailableError
from product_inventory_query_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
RENEW_BEFORE_SECONDS = 60.0


class KeycloakTokenClient:
    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout_seconds
        self._transport = transport
        self._clock = clock
        self._token: str | None = None
        self._valid_until = 0.0
        self._lock = asyncio.Lock()

    def __repr__(self) -> str:  # nunca muestra el secreto ni el token
        return f"KeycloakTokenClient(client_id={self._client_id!r})"

    def invalidate(self) -> None:
        self._token = None
        self._valid_until = 0.0

    async def token(self) -> str:
        if self._token is not None and self._clock() < self._valid_until:
            return self._token
        async with self._lock:
            if self._token is not None and self._clock() < self._valid_until:
                return self._token
            await self._renew()
            assert self._token is not None
            return self._token

    async def _renew(self) -> None:
        data = {"grant_type": "client_credentials", "client_id": self._client_id, "client_secret": self._client_secret}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                response = await client.post(self._token_url, data=data)
        except httpx.HTTPError:
            logger.warning("Keycloak no respondió al pedir el token técnico")
            raise DependencyUnavailableError(KEYCLOAK, "token", "error_de_red") from None
        if response.status_code != 200:
            logger.error("Keycloak rechazó el token técnico estado=%s (revisar el cliente)", response.status_code)
            raise DependencyUnavailableError(KEYCLOAK, "token", f"estado={response.status_code}")
        try:
            body = response.json()
            token = body["access_token"]
            expires_in = float(body.get("expires_in", 60))
        except (ValueError, KeyError, TypeError):
            raise DependencyUnavailableError(KEYCLOAK, "token", "cuerpo_inesperado") from None
        if not isinstance(token, str) or not token:
            raise DependencyUnavailableError(KEYCLOAK, "token", "cuerpo_inesperado")
        self._token = token
        self._valid_until = self._clock() + max(expires_in - RENEW_BEFORE_SECONDS, 0.0)
