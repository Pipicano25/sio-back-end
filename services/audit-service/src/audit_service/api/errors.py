"""Traducción de errores a Problem Details (RFC 9457) con `code` y `trace_id` (D3).

Único módulo que asigna estados HTTP (Principio XII; `contracts/errors.md`).
Regla D11 provisional: `400` solo si el cuerpo JSON no se puede interpretar;
`422` validación; `409` conflicto de `event_id`; `404` inexistente o fuera del
alcance; `503` dependencia no disponible con la extensión `dependency`.

Ninguna respuesta de error incluye `previous_values`, `new_values` ni valores
redactados (FR-004). La base propia no disponible (Principio X) se traduce a
`503 DEPENDENCY_UNAVAILABLE` con `dependency: database`; cualquier otro error
de PostgreSQL conserva su respuesta `500`.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

from audit_service.application.exceptions import AuditError, DependencyUnavailableError
from audit_service.observability import SERVICE_LOGGER

CODE_PREFIX = "AUDIT."
ERROR_TYPE_BASE = "https://sio/errors/audit"
PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(SERVICE_LOGGER)

DATABASE_UNAVAILABLE_DETAIL = (
    "La base de datos del servicio no está disponible temporalmente. Intente de nuevo más tarde."
)
_DISCONNECT_SQLSTATES = frozenset({"57P01", "57P02", "57P03"})

_STATUS_BY_CODE: dict[str, int] = {
    "FORBIDDEN": 403,
    "OPERATIONAL_ACCESS_DENIED": 403,
    "NOT_FOUND": 404,
    "VALIDATION_ERROR": 422,
    "EVENT_ID_CONFLICT": 409,
    "DEPENDENCY_UNAVAILABLE": 503,
}

_HTTP_CODES = {
    400: ("MALFORMED_BODY", "Solicitud mal formada"),
    401: ("UNAUTHENTICATED", "No autenticado"),
    403: ("FORBIDDEN", "Acceso denegado"),
    404: ("NOT_FOUND", "Recurso no encontrado"),
    405: ("METHOD_NOT_ALLOWED", "Método no permitido"),
}


def is_database_unavailable(exc: Exception) -> bool:
    """Indica si el error es la pérdida o indisponibilidad de la conexión con PostgreSQL."""
    if isinstance(exc, InterfaceError):
        return True

    if not isinstance(exc, OperationalError):
        return False

    if exc.connection_invalidated:
        return True

    sqlstate = getattr(exc.orig, "sqlstate", None)
    return sqlstate is None or sqlstate.startswith("08") or sqlstate in _DISCONNECT_SQLSTATES


def problem_response(
    request: Request,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    extra: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Construye una respuesta `application/problem+json`."""
    body: dict[str, Any] = {
        "type": f"{ERROR_TYPE_BASE}/{code.lower().replace('_', '-')}",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        "code": f"{CODE_PREFIX}{code}",
        "trace_id": getattr(request.state, "trace_id", None),
    }

    if extra:
        body.update(extra)

    return JSONResponse(
        status_code=status,
        content=body,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=headers,
    )


def field_path(loc: tuple[Any, ...]) -> str:
    """Ruta de un campo de la solicitud: `events[3].action`, `page_size`."""
    parts = loc[1:] if len(loc) > 1 and loc[0] in {"body", "query", "path"} else loc
    path = ""

    for part in parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else str(part)

    return path


async def _handle_application_error(request: Request, exc: AuditError) -> JSONResponse:
    status = _STATUS_BY_CODE.get(exc.code)

    if status is None:
        logger.error("Código de error sin estado HTTP asignado: %s", exc.code)
        return problem_response(
            request,
            status=500,
            code="INTERNAL_ERROR",
            title="Error interno",
            detail="Ocurrió un error inesperado. Informe el trace_id al soporte.",
        )

    extra: dict[str, Any] = dict(exc.context)

    if isinstance(exc, DependencyUnavailableError):
        # La causa real queda en el log con el trace_id; nunca en la respuesta.
        logger.warning(
            "Dependencia no disponible proveedor=%s operacion=%s causa=%s",
            exc.provider,
            exc.operation,
            exc.cause,
        )
        extra["dependency"] = exc.provider

    errors = list(exc.errors)

    if exc.field:
        errors.append({"field": exc.field, "message": exc.message, "code": exc.code})

    if errors:
        extra["errors"] = errors

    return problem_response(
        request,
        status=status,
        code=exc.code,
        title=exc.title,
        detail=exc.message,
        extra=extra or None,
    )


def _validation_message(error: dict[str, Any]) -> str:
    return str(error.get("msg", "")).removeprefix("Value error, ")


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()

    if any(error.get("type") == "json_invalid" for error in errors):
        return problem_response(
            request,
            status=400,
            code="MALFORMED_BODY",
            title="Solicitud mal formada",
            detail="El cuerpo de la solicitud no es un JSON válido.",
        )

    # Nunca se devuelve `input`: podría contener valores del evento (FR-004).
    return problem_response(
        request,
        status=422,
        code="VALIDATION_ERROR",
        title="Solicitud inválida",
        detail="La solicitud contiene datos inválidos.",
        extra={
            "errors": [
                {
                    "field": field_path(tuple(error.get("loc", ()))),
                    "message": _validation_message(error),
                    "code": "VALIDATION_ERROR",
                }
                for error in errors
            ]
        },
    )


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, title = _HTTP_CODES.get(exc.status_code, ("HTTP_ERROR", "Error"))
    detail = exc.detail if isinstance(exc.detail, str) else title

    return problem_response(
        request,
        status=exc.status_code,
        code=code,
        title=title,
        detail=detail,
        headers=getattr(exc, "headers", None),
    )


async def _handle_database_unavailable(request: Request, exc: Exception) -> JSONResponse:
    if not is_database_unavailable(exc):
        raise exc

    orig = getattr(exc, "orig", exc)
    logger.warning(
        "PostgreSQL no disponible metodo=%s ruta=%s causa=%s sqlstate=%s",
        request.method,
        request.url.path,
        type(orig).__name__,
        getattr(orig, "sqlstate", None),
    )
    return problem_response(
        request,
        status=503,
        code="DEPENDENCY_UNAVAILABLE",
        title="Dependencia no disponible",
        detail=DATABASE_UNAVAILABLE_DETAIL,
        extra={"dependency": "database"},
    )


def register_error_handlers(app: FastAPI) -> None:
    """Registra los manejadores de errores en la aplicación."""
    app.add_exception_handler(AuditError, _handle_application_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(OperationalError, _handle_database_unavailable)
    app.add_exception_handler(InterfaceError, _handle_database_unavailable)
