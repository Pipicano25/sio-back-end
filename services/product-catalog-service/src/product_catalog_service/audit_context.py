"""Autor de auditoría de la solicitud en curso (feature 016; research R-04).

Una dependencia asíncrona de la aplicación copia de `request.state.sio_claims` (fijado
por `sio-auth`) el `sub` y el `preferred_username` del token a un `ContextVar`. Las
dependencias y rutas síncronas se ejecutan con una copia de ese contexto, así que los
repositorios lo leen sin cambiar sus firmas. Sin autor (p. ej. `seed`) no se audita.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import UUID

from fastapi import Request

from product_catalog_service.api.tracing import current_trace_id

USERNAME_MAX_LENGTH = 160


@dataclass(frozen=True, slots=True)
class AuditActor:
    """Identidad autenticada que ejecuta la escritura (humana o técnica)."""

    subject: str
    username: str | None


_actor: ContextVar[AuditActor | None] = ContextVar("audit_actor", default=None)


async def bind_audit_actor(request: Request) -> None:
    """Dependencia de aplicación: fija el autor de la solicitud si hay token validado."""
    claims = getattr(request.state, "sio_claims", None)
    if claims is not None:
        username = claims.preferred_username
        _actor.set(AuditActor(claims.subject, username[:USERNAME_MAX_LENGTH] if username else None))


def current_actor() -> AuditActor | None:
    """Autor de la solicitud en curso, o `None` fuera de una solicitud autenticada."""
    return _actor.get()


def set_actor(actor: AuditActor | None):
    """Fija el autor explícitamente (pruebas y procesos); devuelve el token para restaurarlo."""
    return _actor.set(actor)


def reset_actor(token) -> None:
    _actor.reset(token)


def current_request_id() -> UUID | None:
    """`trace_id` de la solicitud como UUID (como Purchase y Sales)."""
    trace_id = current_trace_id()
    try:
        return UUID(hex=trace_id) if trace_id else None
    except ValueError:
        return None
