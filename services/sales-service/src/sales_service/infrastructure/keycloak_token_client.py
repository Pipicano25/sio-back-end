"""Token técnico `client_credentials` del cliente propio `sales-service` (D5, R-06).

No valida tokens (eso sigue en `sio-auth`, Principio V) y nunca registra ni expone
el token ni el secreto (Principio IX). Un fallo al obtenerlo se expone como
indisponibilidad de la dependencia que se intentaba consultar; la causa queda en
el log.
"""

from __future__ import annotations

import logging
import threading
import time

import httpx

from sales_service.application.exceptions import DependencyUnavailableError
from sales_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)

REFRESH_MARGIN_SECONDS = 60
"""Con menos de estos segundos de vida el token se renueva antes de usarlo (R-06)."""

BACKGROUND_MARGIN_SECONDS = 120
"""Con menos de estos segundos de vida se renueva en segundo plano y se sigue usando el vigente: Keycloak
puede tardar segundos en emitir un token y ninguna solicitud debe esperarlo mientras el actual sirva."""


def _daemon(task) -> None:
    threading.Thread(target=task, name="renovacion-token-tecnico", daemon=True).start()

KEYCLOAK_TOKEN_REJECTED = "keycloak_token_rejected"


class TokenUnavailableError(Exception):
    """Keycloak no entregó el token; el adaptador lo traduce a su dependencia."""


class KeycloakTokenClient:
    """Obtiene y reutiliza en memoria el token técnico; lo renueva en segundo plano antes de que expire."""

    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
        clock=time.monotonic,
        background=_daemon,
    ) -> None:
        self._token_url = token_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._clock = clock
        self._lock = threading.Lock()
        self._token: str | None = None
        self._expires_at = 0.0
        self._background = background
        self._renewing = False

    def __repr__(self) -> str:  # nunca muestra el secreto ni el token
        return f"KeycloakTokenClient(client_id={self._client_id!r})"

    def get_token(self) -> str:
        """Devuelve un token vigente, pidiéndolo si hace falta.

        Raises:
            TokenUnavailableError: Si Keycloak no entrega el token.
        """
        with self._lock:
            remaining = self._expires_at - self._clock()
            if self._token is not None and remaining > REFRESH_MARGIN_SECONDS:
                if remaining <= BACKGROUND_MARGIN_SECONDS and not self._renewing:
                    self._renewing = True
                    self._background(self._renew)
                return self._token

            self._token, lifetime = self._request_token()
            self._expires_at = self._clock() + lifetime
            return self._token

    def _renew(self) -> None:
        """Renovación anticipada (fuera del bloqueo): si falla, se conserva el token vigente."""
        try:
            token, lifetime = self._request_token()
        except TokenUnavailableError:
            with self._lock:
                self._renewing = False
            return
        with self._lock:
            self._token = token
            self._expires_at = self._clock() + lifetime
            self._renewing = False

    def invalidate(self) -> None:
        """Descarta el token en memoria (tras un `401` del proveedor)."""
        with self._lock:
            self._token = None
            self._expires_at = 0.0
            self._renewing = False

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
        lifetime = body.get("expires_in", 300) if isinstance(body, dict) else 300

        if not isinstance(token, str) or not token:
            raise self._rejected("cuerpo_inesperado")

        try:
            lifetime = float(lifetime)
        except (TypeError, ValueError):
            lifetime = 300.0

        return token, lifetime

    def _rejected(self, outcome: str) -> TokenUnavailableError:
        logger.error(
            "No fue posible obtener el token técnico causa=%s cliente=%s resultado=%s",
            KEYCLOAK_TOKEN_REJECTED,
            self._client_id,
            outcome,
        )
        return TokenUnavailableError(outcome)


def technical_dependency_error(provider: str, operation: str) -> DependencyUnavailableError:
    """Indisponibilidad de `provider` por no poder obtener el token técnico."""
    return DependencyUnavailableError(provider, operation=operation, cause=KEYCLOAK_TOKEN_REJECTED)
