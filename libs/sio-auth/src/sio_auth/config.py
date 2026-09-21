"""Configuración de la librería de autenticación de SIO.

El punto de entrada público es :meth:`AuthSettings.from_env`. La configuración
se mantiene explícita para que todos los microservicios utilicen el mismo
contrato con Keycloak sin duplicar detalles de JWT/JWKS.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping
from urllib.parse import urlparse

from .errors import AuthConfigurationError

DEFAULT_AUDIENCE = "sio-api"
DEFAULT_HTTP_TIMEOUT_SECONDS = 5.0
DEFAULT_JWKS_CACHE_TTL_SECONDS = 300.0
DEFAULT_ENV_PREFIX = "SIO_AUTH_"
REQUIRED_ALGORITHM = "RS256"


def _required_text(value: str | None, *, name: str) -> str:
    if value is None or not value.strip():
        raise AuthConfigurationError(f"{name} es obligatorio y no puede estar vacío")
    return value.strip()


def _http_url(value: str, *, name: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AuthConfigurationError(
            f"{name} debe ser una URL absoluta http:// o https://"
        )
    return value.rstrip("/")


def _positive_float(value: str | float, *, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise AuthConfigurationError(f"{name} debe ser un número") from exc

    if number <= 0:
        raise AuthConfigurationError(f"{name} debe ser mayor que cero")
    return number


@dataclass(frozen=True, slots=True)
class AuthSettings:
    """Configuración inmutable compartida por todos los componentes de autenticación.

    ``algorithm`` no es configurable de forma intencional. El contrato de
    seguridad de SIO exige RS256; permitir cambiarlo mediante una variable de
    entorno podría habilitar accidentalmente una degradación del algoritmo.
    """

    issuer: str
    audience: str = DEFAULT_AUDIENCE
    jwks_url: str | None = None
    http_timeout_seconds: float = DEFAULT_HTTP_TIMEOUT_SECONDS
    jwks_cache_ttl_seconds: float = DEFAULT_JWKS_CACHE_TTL_SECONDS

    def __post_init__(self) -> None:
        issuer = _http_url(
            _required_text(self.issuer, name="issuer"),
            name="issuer",
        )
        audience = _required_text(self.audience, name="audience")

        jwks_url = self.jwks_url
        if jwks_url is None:
            jwks_url = f"{issuer}/protocol/openid-connect/certs"
        else:
            jwks_url = _http_url(
                _required_text(jwks_url, name="jwks_url"),
                name="jwks_url",
            )

        timeout = _positive_float(
            self.http_timeout_seconds,
            name="http_timeout_seconds",
        )
        cache_ttl = _positive_float(
            self.jwks_cache_ttl_seconds,
            name="jwks_cache_ttl_seconds",
        )

        object.__setattr__(self, "issuer", issuer)
        object.__setattr__(self, "audience", audience)
        object.__setattr__(self, "jwks_url", jwks_url)
        object.__setattr__(self, "http_timeout_seconds", timeout)
        object.__setattr__(self, "jwks_cache_ttl_seconds", cache_ttl)

    @property
    def algorithm(self) -> str:
        """Algoritmo de firma JWT aceptado por SIO."""

        return REQUIRED_ALGORITHM

    @classmethod
    def from_env(
        cls,
        *,
        prefix: str = DEFAULT_ENV_PREFIX,
        environ: Mapping[str, str] | None = None,
    ) -> "AuthSettings":
        """Construye la configuración a partir de variables de entorno.

        Obligatoria:
            ``SIO_AUTH_ISSUER``

        Opcionales:
            ``SIO_AUTH_AUDIENCE`` (valor predeterminado: ``sio-api``)
            ``SIO_AUTH_JWKS_URL`` (se deriva del issuer si no se define)
            ``SIO_AUTH_HTTP_TIMEOUT_SECONDS`` (valor predeterminado: 5)
            ``SIO_AUTH_JWKS_CACHE_TTL_SECONDS`` (valor predeterminado: 300)

        ``environ`` permite proporcionar explícitamente un conjunto de variables
        de entorno cuando sea necesario; los microservicios normalmente no deben
        utilizar este parámetro.
        """

        env = os.environ if environ is None else environ

        issuer = env.get(f"{prefix}ISSUER")
        audience = env.get(f"{prefix}AUDIENCE", DEFAULT_AUDIENCE)
        jwks_url = env.get(f"{prefix}JWKS_URL")
        timeout = env.get(
            f"{prefix}HTTP_TIMEOUT_SECONDS",
            str(DEFAULT_HTTP_TIMEOUT_SECONDS),
        )
        cache_ttl = env.get(
            f"{prefix}JWKS_CACHE_TTL_SECONDS",
            str(DEFAULT_JWKS_CACHE_TTL_SECONDS),
        )

        return cls(
            issuer=_required_text(
                issuer,
                name=f"{prefix}ISSUER",
            ),
            audience=audience,
            jwks_url=jwks_url,
            http_timeout_seconds=_positive_float(
                timeout,
                name=f"{prefix}HTTP_TIMEOUT_SECONDS",
            ),
            jwks_cache_ttl_seconds=_positive_float(
                cache_ttl,
                name=f"{prefix}JWKS_CACHE_TTL_SECONDS",
            ),
        )
