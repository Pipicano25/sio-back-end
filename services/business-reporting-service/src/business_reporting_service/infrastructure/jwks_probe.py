"""Comprobación de disponibilidad del JWKS de Keycloak para `/health/ready` (spec 023).

No valida tokens (eso lo hace `sio-auth`): solo comprueba que el documento JWKS responde con
claves. Keycloak es un servicio de clase B; el servicio no consulta aquí dependencias de clase C.
"""

from __future__ import annotations

import logging

import httpx

from business_reporting_service.api.health import ReadinessProbe
from business_reporting_service.config import Settings
from business_reporting_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
JWKS_TIMEOUT_SECONDS = 2.0


def build_jwks_probe(settings: Settings, transport: httpx.BaseTransport | None = None) -> ReadinessProbe:
    """Construye la comprobación. Sin `SIO_AUTH_JWKS_URL` la aplicación no está lista."""

    def probe() -> bool:
        if not settings.jwks_url:
            return False

        try:
            with httpx.Client(timeout=JWKS_TIMEOUT_SECONDS, transport=transport) as client:
                response = client.get(settings.jwks_url)
            keys = response.json().get("keys") if response.status_code == 200 else None
        except (httpx.HTTPError, ValueError, AttributeError) as exc:
            logger.warning("JWKS no disponible causa=%s", type(exc).__name__)
            return False

        return isinstance(keys, list) and bool(keys)

    return probe
