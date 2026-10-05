"""Traducción a HTTP de errores controlados (feature 008).

- Los dos `409` de `GlobalPaymentConditionType` añaden `code` al cuerpo vigente
  `{"detail": …}` (DS-04); el resto de errores conserva su formato (RFC 9457 diferido,
  GAP-PR-15).
- PostgreSQL no disponible → `503 {"detail": …}` controlado en lugar de un `500`
  (GAP-PR-19); la causa técnica solo va al log. Desde la feature 009 (FR-014,
  alineación correctiva) solo la pérdida o indisponibilidad de la conexión produce
  ese `503` (`is_database_unavailable`, mismo criterio que los demás servicios);
  cualquier otro error de PostgreSQL (deadlock, serialización, cancelación,
  bloqueo) vuelve a su `500` no controlado.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError

from payment_reference_service.application.exceptions import (
    GlobalPaymentConditionTypeVersionConflictError,
    InvalidStatusTransitionError,
)

logger = logging.getLogger("payment_reference_service")

DATABASE_UNAVAILABLE_DETAIL = (
    "Payment Reference no puede atender la solicitud porque su base de datos no está "
    "disponible. Intente de nuevo en unos momentos."
)

_DISCONNECT_SQLSTATES = frozenset({"57P01", "57P02", "57P03"})

VERSION_CONFLICT = "PAYMENT_REFERENCE.VERSION_CONFLICT"
INVALID_STATUS_TRANSITION = "PAYMENT_REFERENCE.INVALID_STATUS_TRANSITION"


def is_database_unavailable(exc: Exception) -> bool:
    """Indica si el error es la pérdida o indisponibilidad de la conexión con PostgreSQL.

    `True` para `InterfaceError` (conexión cerrada) y para `OperationalError` con la
    conexión invalidada por SQLAlchemy, sin SQLSTATE (el servidor no respondió), con
    SQLSTATE de clase `08` o `57P01`/`57P02`/`57P03`. `False` para todo lo demás
    (p. ej. deadlock `40P01`, serialización `40001`, cancelación `57014`, bloqueo `55P03`).
    """
    if isinstance(exc, InterfaceError):
        return True

    if not isinstance(exc, OperationalError):
        return False

    if exc.connection_invalidated:
        return True

    sqlstate = getattr(exc.orig, "sqlstate", None)
    return sqlstate is None or sqlstate.startswith("08") or sqlstate in _DISCONNECT_SQLSTATES


def _conflict(detail: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": detail, "code": code},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Registra los manejadores de los dos conflictos con `code`."""

    @app.exception_handler(GlobalPaymentConditionTypeVersionConflictError)
    async def version_conflict(
        request: Request,
        exc: GlobalPaymentConditionTypeVersionConflictError,
    ) -> JSONResponse:
        return _conflict(str(exc), VERSION_CONFLICT)

    @app.exception_handler(InvalidStatusTransitionError)
    async def invalid_transition(
        request: Request,
        exc: InvalidStatusTransitionError,
    ) -> JSONResponse:
        return _conflict(str(exc), INVALID_STATUS_TRANSITION)

    async def database_unavailable(request: Request, exc: Exception) -> JSONResponse:
        if not is_database_unavailable(exc):
            # Otro error de PostgreSQL: conserva su `500` no controlado.
            raise exc

        orig = getattr(exc, "orig", exc)
        logger.warning(
            "PostgreSQL no disponible metodo=%s ruta=%s causa=%s sqlstate=%s",
            request.method,
            request.url.path,
            type(orig).__name__,
            getattr(orig, "sqlstate", None),
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": DATABASE_UNAVAILABLE_DETAIL},
        )

    app.add_exception_handler(OperationalError, database_unavailable)
    app.add_exception_handler(InterfaceError, database_unavailable)
