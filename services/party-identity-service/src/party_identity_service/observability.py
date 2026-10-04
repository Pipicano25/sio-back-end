"""Contexto de trazabilidad y logging con `trace_id` (D3, D14 provisional).

Módulo neutral: lo usan la capa API (middleware) y los adaptadores salientes
(propagación de `traceparent` a Geography) sin depender entre sí.
"""

from __future__ import annotations

import logging
import secrets
from contextvars import ContextVar

SERVICE_LOGGER = "party_identity_service"
NO_TRACE = "-"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] trace_id=%(trace_id)s %(message)s"
# `sio_auth` registra las denegaciones por permiso (el permiso no viaja en el `403`).
AUTH_LOGGER = "sio_auth"
TRACED_LOGGERS = (SERVICE_LOGGER, AUTH_LOGGER, "uvicorn", "uvicorn.error", "uvicorn.access")

_current_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def current_trace_id() -> str | None:
    """`trace_id` de la solicitud en curso, si existe."""
    return _current_trace_id.get()


def set_trace_id(trace_id: str):
    """Fija el `trace_id` de la solicitud en curso; devuelve el token para restaurarlo."""
    return _current_trace_id.set(trace_id)


def reset_trace_id(token) -> None:
    """Restaura el `trace_id` anterior."""
    _current_trace_id.reset(token)


def build_traceparent(trace_id: str) -> str:
    """Construye una cabecera W3C `traceparent` con un span nuevo."""
    return f"00-{trace_id}-{secrets.token_hex(8)}-01"


class TraceIdFilter(logging.Filter):
    """Copia el `trace_id` de la solicitud en curso en cada registro de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "trace_id", None):
            record.trace_id = current_trace_id() or NO_TRACE
        return True


def configure_logging() -> None:
    """Agrega el `trace_id` al formato de los loggers del servicio y de uvicorn.

    Es idempotente: puede llamarse en cada `create_app()`.
    """
    formatter = logging.Formatter(LOG_FORMAT)

    for name in TRACED_LOGGERS:
        logger = logging.getLogger(name)

        if not any(isinstance(item, TraceIdFilter) for item in logger.filters):
            logger.addFilter(TraceIdFilter())

        for handler in logger.handlers:
            if not any(isinstance(item, TraceIdFilter) for item in handler.filters):
                handler.addFilter(TraceIdFilter())
            handler.setFormatter(formatter)

    for name in (SERVICE_LOGGER, AUTH_LOGGER):
        service_logger = logging.getLogger(name)

        if not service_logger.handlers:
            handler = logging.StreamHandler()
            handler.addFilter(TraceIdFilter())
            handler.setFormatter(formatter)
            service_logger.addHandler(handler)
            service_logger.setLevel(logging.INFO)
