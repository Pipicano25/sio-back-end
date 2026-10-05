"""Base de datos no disponible → `503 {"detail": …}` (feature 009, Constitución 2.4.0).

Cambio transversal mínimo sobre la línea base AS-IS: solo la pérdida o indisponibilidad de la
conexión con PostgreSQL se responde con `503` en el formato vigente del servicio (`{"detail": …}`, sin
`code` ni `trace_id`). Cualquier otro error de PostgreSQL conserva su `500` AS-IS.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError

logger = logging.getLogger("geography_service")

DATABASE_UNAVAILABLE_DETAIL = (
    "La base de datos del servicio no está disponible temporalmente. Intente de nuevo más tarde."
)
_DISCONNECT_SQLSTATES = frozenset({"57P01", "57P02", "57P03"})


def is_database_unavailable(exc: Exception) -> bool:
    """Indica si el error es la pérdida o indisponibilidad de la conexión con PostgreSQL.

    `True` para `InterfaceError` (conexión cerrada) y para `OperationalError` con la conexión
    invalidada por SQLAlchemy, sin SQLSTATE (el servidor no respondió), con SQLSTATE de clase `08` o
    `57P01`/`57P02`/`57P03`. `False` para todo lo demás (p. ej. deadlock `40P01`, serialización
    `40001`, cancelación `57014`, bloqueo `55P03`).
    """
    if isinstance(exc, InterfaceError):
        return True

    if not isinstance(exc, OperationalError):
        return False

    if exc.connection_invalidated:
        return True

    sqlstate = getattr(exc.orig, "sqlstate", None)
    return sqlstate is None or sqlstate.startswith("08") or sqlstate in _DISCONNECT_SQLSTATES


async def _database_unavailable(request: Request, exc: Exception) -> JSONResponse:
    if not is_database_unavailable(exc):
        # Otro error de PostgreSQL: conserva el `500` AS-IS.
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


def register_database_unavailable_handler(app: FastAPI) -> None:
    """Registra la traducción de la pérdida de conexión con PostgreSQL a `503`."""
    app.add_exception_handler(OperationalError, _database_unavailable)
    app.add_exception_handler(InterfaceError, _database_unavailable)
