"""Contexto de trazabilidad y logging con `trace_id` (D3, D14 provisional; spec 023).

Módulo neutral: lo usan la capa API (middleware) y los adaptadores salientes (propagación de
`traceparent`). `SecretRedactionFilter` impide que un `Authorization` o un token Bearer o JWT lleguen al
log, aunque algún mensaje los incluya por error (el servicio propaga el token del usuario, DR-07).
"""

from __future__ import annotations

import logging
import re
import secrets
from contextvars import ContextVar

SERVICE_LOGGER = "business_reporting_service"
NO_TRACE = "-"
REDACTED = "[REDACTADO]"
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] trace_id=%(trace_id)s %(message)s"
# `sio_auth` registra las denegaciones por permiso (el permiso no viaja en el `403`).
AUTH_LOGGER = "sio_auth"
TRACED_LOGGERS = (SERVICE_LOGGER, AUTH_LOGGER, "uvicorn", "uvicorn.error", "uvicorn.access")

_SENSITIVE = (
    re.compile(r"(?i)(authorization\s*[:=]\s*)(bearer\s+)?\S+"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-_.=]+"),
    re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}(\.[A-Za-z0-9_\-]*)?"),
)

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


def redact(text: str) -> str:
    """Reemplaza tokens por un marcador."""
    for pattern in _SENSITIVE:
        text = pattern.sub(REDACTED, text)
    return text


class TraceIdFilter(logging.Filter):
    """Copia el `trace_id` de la solicitud en curso en cada registro de log."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "trace_id", None):
            record.trace_id = current_trace_id() or NO_TRACE
        return True


class SecretRedactionFilter(logging.Filter):
    """Elimina del mensaje final cualquier secreto reconocible (spec 023: tokens nunca en logs)."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        cleaned = redact(message)

        if cleaned != message:
            record.msg = cleaned
            record.args = None

        return True


def _ensure_filters(target: logging.Filterer) -> None:
    if not any(isinstance(item, TraceIdFilter) for item in target.filters):
        target.addFilter(TraceIdFilter())
    if not any(isinstance(item, SecretRedactionFilter) for item in target.filters):
        target.addFilter(SecretRedactionFilter())


def configure_logging() -> None:
    """Agrega el `trace_id` y la redacción a los loggers del servicio y de uvicorn (idempotente)."""
    formatter = logging.Formatter(LOG_FORMAT)

    for name in TRACED_LOGGERS:
        logger = logging.getLogger(name)
        _ensure_filters(logger)

        for handler in logger.handlers:
            _ensure_filters(handler)
            handler.setFormatter(formatter)

    for name in (SERVICE_LOGGER, AUTH_LOGGER):
        service_logger = logging.getLogger(name)

        if not service_logger.handlers:
            handler = logging.StreamHandler()
            _ensure_filters(handler)
            handler.setFormatter(formatter)
            service_logger.addHandler(handler)
            service_logger.setLevel(logging.INFO)
