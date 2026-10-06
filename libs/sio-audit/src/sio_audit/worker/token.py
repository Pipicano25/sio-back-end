"""Token `client_credentials` del emisor (D5). Nunca se registra en logs."""

from __future__ import annotations

import time

import httpx


class TokenUnavailableError(RuntimeError):
    """No se pudo obtener el token técnico (se trata como Audit no disponible)."""


class ClientCredentialsToken:
    """Obtiene y reutiliza el token hasta 30 s antes de su vencimiento."""

    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout_seconds
        self._transport = transport
        self._token: str | None = None
        self._expires_at = 0.0

    def get(self) -> str:
        if self._token is None or time.monotonic() >= self._expires_at:
            self._fetch()
        assert self._token is not None
        return self._token

    def invalidate(self) -> None:
        self._token = None
        self._expires_at = 0.0

    def _fetch(self) -> None:
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(
                    self._token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                    },
                )
        except httpx.HTTPError as exc:
            raise TokenUnavailableError(type(exc).__name__) from None

        if response.status_code != 200:
            raise TokenUnavailableError(f"estado={response.status_code}")

        body = response.json()
        self._token = body["access_token"]
        self._expires_at = time.monotonic() + max(float(body.get("expires_in", 60)) - 30, 5)
