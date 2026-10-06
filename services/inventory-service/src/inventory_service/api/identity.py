"""Identidad técnica de la solicitud (RC-01; research.md R-02, R-08).

Aplicar o revertir operaciones exige el permiso del tipo **y** que el token sea de
una cuenta de servicio: `client_id` y `preferred_username` presentes y
`preferred_username == "service-account-" + client_id` (correlación R-11 de la
007, igual que Audit). Si falla, se responde el mismo `403` que la falta de
permiso (`FORBIDDEN_DETAIL` de `sio-auth`), sin revelar el motivo; el motivo
queda solo en el log.

La lectura técnica sin membresía (DS-12) exige además
`perm:inventory:platform:lookup`, evaluado con `sio_auth.evaluate_permission`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status
from sio_auth import FORBIDDEN_DETAIL, SioPermission, evaluate_permission
from sio_auth.dependencies import get_current_claims

from inventory_service.observability import SERVICE_LOGGER

SERVICE = "inventory"
SERVICE_ACCOUNT_PREFIX = "service-account-"
PLATFORM_LOOKUP = SioPermission(service=SERVICE, resource="platform", action="lookup")

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


def has_platform_lookup(roles: Iterable[str]) -> bool:
    """Indica si los roles conceden `perm:inventory:platform:lookup`."""
    return evaluate_permission(roles, PLATFORM_LOOKUP)


@dataclass(frozen=True, slots=True)
class RequestIdentity:
    """Identidad autenticada de la solicitud."""

    subject: str
    client_id: str | None
    authorization: str | None

    @property
    def is_service_account(self) -> bool:
        return self.client_id is not None


@dataclass(frozen=True, slots=True)
class ServiceIdentity:
    """Cuenta de servicio que aplica o revierte operaciones."""

    subject: str
    client_id: str


def get_identity(request: Request) -> RequestIdentity:
    claims = get_current_claims(request)
    return RequestIdentity(
        subject=claims.subject.strip(),
        client_id=service_account_client_id(claims.raw),
        authorization=request.headers.get("authorization"),
    )


def technical_lookup(request: Request) -> bool:
    """Cuenta de servicio con `perm:inventory:platform:lookup` (DS-12)."""
    claims = get_current_claims(request)
    return service_account_client_id(claims.raw) is not None and has_platform_lookup(claims.roles)


def require_service_account(request: Request) -> ServiceIdentity:
    """Dependencia de las rutas que aplican o revierten: solo cuentas de servicio."""
    identity = get_identity(request)

    if identity.client_id is None or not identity.subject:
        logger.warning(
            "Operación de inventario denegada: el token no es de una cuenta de servicio "
            "sujeto=%s metodo=%s ruta=%s",
            identity.subject,
            request.method,
            request.url.path,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_DETAIL)

    return ServiceIdentity(subject=identity.subject, client_id=identity.client_id)
