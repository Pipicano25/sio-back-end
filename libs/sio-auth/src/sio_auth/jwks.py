"""Obtención de JWKS y caché de claves públicas segura para concurrencia."""

from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Any, Callable

import httpx
import jwt

from .config import AuthSettings
from .errors import AuthenticationError

_UNKNOWN_KID_RETRY_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class _CachedKey:
    key: Any
    expires_at: float


class JWKSClient:
    """Resuelve claves de firma de Keycloak por ``kid`` con una caché acotada.

    El objeto puede compartirse de forma segura entre solicitudes concurrentes.
    Utiliza ``threading.RLock`` al modificar o actualizar la caché porque la
    validación del token se ejecuta en el pool de hilos de trabajo de FastAPI.

    Ninguna clave de firma se conserva indefinidamente: cuando vence su TTL,
    Keycloak debe volver a publicarla correctamente antes de poder reutilizarla.
    """

    def __init__(
        self,
        settings: AuthSettings,
        *,
        client: httpx.Client | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._settings = settings
        self._client = client or httpx.Client(
            timeout=settings.http_timeout_seconds,
        )
        self._owns_client = client is None
        self._clock = clock
        self._lock = threading.RLock()
        self._keys: dict[str, _CachedKey] = {}
        self._missing_kids_until: dict[str, float] = {}

    def get_signing_key(self, kid: str) -> Any:
        """Devuelve la clave pública para ``kid`` o deniega el acceso de forma segura."""

        if not isinstance(kid, str) or not kid.strip():
            raise AuthenticationError("El encabezado del token de acceso no contiene kid")
        kid = kid.strip()

        with self._lock:
            now = self._clock()
            cached = self._keys.get(kid)
            if cached is not None and cached.expires_at > now:
                return cached.key

            retry_after = self._missing_kids_until.get(kid, 0.0)
            if retry_after > now:
                raise AuthenticationError("La clave de firma del token es desconocida")

            self._refresh_locked(now)
            cached = self._keys.get(kid)
            if cached is None or cached.expires_at <= self._clock():
                self._missing_kids_until[kid] = (
                    self._clock() + _UNKNOWN_KID_RETRY_SECONDS
                )
                raise AuthenticationError("La clave de firma del token es desconocida")
            return cached.key

    def _refresh_locked(self, now: float) -> None:
        try:
            response = self._client.get(self._settings.jwks_url)
            response.raise_for_status()
            document = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AuthenticationError("No fue posible obtener las claves de firma de Keycloak") from exc

        keys = document.get("keys") if isinstance(document, dict) else None
        if not isinstance(keys, list):
            raise AuthenticationError("Keycloak devolvió un documento JWKS inválido")

        expires_at = now + self._settings.jwks_cache_ttl_seconds
        fresh: dict[str, _CachedKey] = {}

        for item in keys:
            if not isinstance(item, dict):
                continue
            kid = item.get("kid")
            if not isinstance(kid, str) or not kid:
                continue
            if item.get("kty") != "RSA":
                continue
            if item.get("use") not in {None, "sig"}:
                continue
            if item.get("alg") not in {None, self._settings.algorithm}:
                continue

            try:
                public_key = jwt.PyJWK.from_dict(item).key
            except (jwt.PyJWKError, ValueError, TypeError):
                continue
            fresh[kid] = _CachedKey(public_key, expires_at)

        if not fresh:
            raise AuthenticationError("El JWKS de Keycloak no contiene claves RS256 utilizables")

        self._keys = fresh
        self._missing_kids_until = {
            missing_kid: retry_until
            for missing_kid, retry_until in self._missing_kids_until.items()
            if retry_until > now
        }

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "JWKSClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
