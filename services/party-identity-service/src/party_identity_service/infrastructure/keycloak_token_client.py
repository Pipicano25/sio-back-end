"""Obtención de un token técnico `client_credentials` (D5, FR-018, R-06).

Lo usan el `seed` en modo Geography (`fetch_client_credentials_token`) y la API
para consultar Operational Context (`CachedClientCredentialsToken`). No valida
tokens (eso sigue en `sio-auth`, Principio V) y nunca registra ni expone el
secreto ni el token (Principio IX).
"""

import threading
import time

import httpx

# El token en caché se renueva cuando le quedan menos de estos segundos de vida
# (misma política que el cliente técnico de Operational Context).
REFRESH_MARGIN_SECONDS = 30
DEFAULT_LIFETIME_SECONDS = 60.0


class TokenRequestError(RuntimeError):
    """No fue posible obtener el token técnico."""


def fetch_client_credentials_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    *,
    timeout: float,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Pide un `access_token` con el flujo OAuth 2.0 `client_credentials`.

    Args:
        token_url: Endpoint de tokens del realm.
        client_id: Cliente técnico del servicio.
        client_secret: Secreto del cliente (leído del entorno).
        timeout: Tiempo de espera propio de Keycloak
            (`KEYCLOAK_TIMEOUT_SECONDS`).
        transport: Transporte `httpx` opcional para pruebas.

    Returns:
        El `access_token`.

    Raises:
        TokenRequestError: Ante error de red, tiempo agotado o respuesta
            distinta de `200` con token.
    """
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )

    except httpx.HTTPError as exc:
        raise TokenRequestError(
            f"No fue posible contactar a Keycloak ({type(exc).__name__})."
        ) from None

    if response.status_code != 200:
        raise TokenRequestError(
            f"Keycloak rechazó la solicitud de token del cliente {client_id} "
            f"(estado {response.status_code})."
        )

    try:
        return response.json()["access_token"]

    except (ValueError, KeyError, TypeError):
        raise TokenRequestError("Keycloak no devolvió un access_token.") from None


class CachedClientCredentialsToken:
    """Token técnico reutilizado en memoria hasta poco antes de expirar.

    `invalidate()` lo descarta (p. ej. tras un `401` del proveedor) para que la
    siguiente llamada pida uno nuevo. Seguro para hilos.
    """

    def __init__(
        self,
        *,
        token_url: str,
        client_id: str,
        client_secret: str,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
        clock=time.monotonic,
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

    def __repr__(self) -> str:  # nunca muestra el secreto ni el token
        return f"CachedClientCredentialsToken(client_id={self._client_id!r})"

    def get(self) -> str:
        """Devuelve un token vigente, pidiéndolo si hace falta.

        Raises:
            TokenRequestError: Si Keycloak no entrega el token.
        """
        with self._lock:
            if self._token is not None and self._clock() < self._expires_at - REFRESH_MARGIN_SECONDS:
                return self._token

            token, lifetime = _request_token(
                self._token_url,
                self._client_id,
                self._client_secret,
                timeout=self._timeout_seconds,
                transport=self._transport,
            )
            self._token = token
            self._expires_at = self._clock() + lifetime
            return token

    def invalidate(self) -> None:
        """Descarta el token en memoria."""
        with self._lock:
            self._token = None
            self._expires_at = 0.0


def _request_token(
    token_url: str,
    client_id: str,
    client_secret: str,
    *,
    timeout: float,
    transport: httpx.BaseTransport | None,
) -> tuple[str, float]:
    """Pide un token y su vida útil (`expires_in`, 60 s si falta)."""
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
    except httpx.HTTPError as exc:
        raise TokenRequestError(
            f"No fue posible contactar a Keycloak ({type(exc).__name__})."
        ) from None

    if response.status_code != 200:
        raise TokenRequestError(
            f"Keycloak rechazó la solicitud de token del cliente {client_id} "
            f"(estado {response.status_code})."
        )

    try:
        body = response.json()
    except ValueError:
        body = None

    token = body.get("access_token") if isinstance(body, dict) else None
    if not isinstance(token, str) or not token:
        raise TokenRequestError("Keycloak no devolvió un access_token.")

    try:
        lifetime = float(body.get("expires_in", DEFAULT_LIFETIME_SECONDS))
    except (TypeError, ValueError):
        lifetime = DEFAULT_LIFETIME_SECONDS

    return token, lifetime


class MissingClientCredentials:
    """Sustituto cuando faltan las variables del cliente técnico (R-15).

    El servicio arranca y las lecturas funcionan; cualquier operación que
    necesite el token técnico falla con un `TokenRequestError` que nombra las
    variables ausentes (el adaptador lo traduce a `503`, `dependency: keycloak`).
    """

    def __init__(self, missing: list[str]) -> None:
        self.missing = list(missing)

    def __repr__(self) -> str:
        return f"MissingClientCredentials(missing={self.missing!r})"

    def get(self) -> str:
        raise TokenRequestError(
            "Faltan variables del cliente técnico: " + ", ".join(self.missing) + "."
        )

    def invalidate(self) -> None:
        return None
