"""Identidad de la solicitud (RC-05; research.md R-02).

Todas las rutas de negocio de Purchase exigen un **usuario humano**: un token de
cuenta de servicio (`client_id` y `preferred_username == "service-account-" +
client_id`, correlación R-11 de la 007) recibe el mismo `403` que la falta de
permiso (`FORBIDDEN_DETAIL` de `sio-auth`), aunque tenga los permisos por comodín;
el motivo queda solo en el log. En esta fase no hay consumidores técnicos.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status
from sio_auth import FORBIDDEN_DETAIL
from sio_auth.dependencies import get_current_claims

from purchase_service.observability import SERVICE_LOGGER

SERVICE = "purchase"
SERVICE_ACCOUNT_PREFIX = "service-account-"

logger = logging.getLogger(SERVICE_LOGGER)


def service_account_client_id(raw_claims: Mapping[str, Any]) -> str | None:
    """`client_id` si los claims corresponden a una cuenta de servicio; si no, `None`."""
    client_id = raw_claims.get("client_id")
    username = raw_claims.get("preferred_username")

    if not isinstance(client_id, str) or not client_id:
        return None

    if not isinstance(username, str) or not username:
        return None

    if username != f"{SERVICE_ACCOUNT_PREFIX}{client_id}":
        return None

    return client_id


@dataclass(frozen=True, slots=True)
class HumanIdentity:
    """Usuario humano autenticado: su `sub` (D1) y su `Authorization` para Operational Context."""

    subject: str
    authorization: str | None


def require_human_user(request: Request) -> HumanIdentity:
    """Dependencia de todas las rutas de negocio: una cuenta de servicio recibe `403` (RC-05)."""
    claims = get_current_claims(request)
    subject = claims.subject.strip()
    client_id = service_account_client_id(claims.raw)

    if client_id is not None or not subject:
        logger.warning(
            "Solicitud denegada: el token es de una cuenta de servicio sujeto=%s metodo=%s ruta=%s",
            subject,
            request.method,
            request.url.path,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_DETAIL)

    return HumanIdentity(subject=subject, authorization=request.headers.get("authorization"))
