"""Identidad técnica de la solicitud (RC-01, RC-03; R-03).

Registrar eventos exige el permiso **y** que el token sea de una cuenta de
servicio. La correlación es la misma que la de Commercial Relationship (R-11 de
la 007): `client_id` y `preferred_username` presentes y
`preferred_username == "service-account-" + client_id`. `azp` y `sid` no
intervienen. Si falla, se responde el mismo `403` que la falta de permiso
(`FORBIDDEN_DETAIL` de `sio-auth`), sin revelar el motivo; el motivo queda solo
en el log.

`source_service` = `client_id` y `created_by` = `sub` salen siempre del token,
nunca del cuerpo.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status
from sio_auth import FORBIDDEN_DETAIL
from sio_auth.dependencies import get_current_claims

from audit_service.observability import SERVICE_LOGGER

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
class EmitterIdentity:
    """Cuenta de servicio que registra eventos."""

    subject: str
    client_id: str


def require_service_account(request: Request) -> EmitterIdentity:
    """Dependencia de las rutas de registro: solo cuentas de servicio."""
    claims = get_current_claims(request)
    client_id = service_account_client_id(claims.raw)
    subject = claims.subject.strip()

    if client_id is None or not subject:
        logger.warning(
            "Registro de auditoría denegado: el token no es de una cuenta de servicio "
            "sujeto=%s metodo=%s ruta=%s",
            claims.subject,
            request.method,
            request.url.path,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_DETAIL)

    return EmitterIdentity(subject=subject, client_id=client_id)
