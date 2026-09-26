"""Traducción de errores a Problem Details (RFC 9457) con `code` y `trace_id` (D3).

Este módulo es el **único** que asigna estados HTTP (Principio XII): las
excepciones de aplicación solo llevan `code` y mensaje, y la tabla
`_STATUS_BY_CODE` los traduce.

Regla D11 provisional (`contracts/errors.md`): `400` solo si el cuerpo JSON no
se puede interpretar; `422` para toda validación de entrada (cuerpo, ruta y
consulta) y de dominio; `409` unicidad, versión y transición; `404` recurso
de la ruta inexistente; `503` dependencia no disponible.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from party_identity_service.application.exceptions import (
    PartyIdentityError,
)
from party_identity_service.observability import SERVICE_LOGGER

CODE_PREFIX = "PARTY_IDENTITY."
ERROR_TYPE_BASE = "https://sio/errors/party-identity"
PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(SERVICE_LOGGER)

_STATUS_BY_CODE: dict[str, int] = {
    "NOT_FOUND": 404,
    "IMMUTABLE_FIELD": 422,
    "RULE_CHANGE_REQUIRES_NEW_VERSION": 422,
    "INVALID_NUMBER_PATTERN": 422,
    "EXAMPLE_DOES_NOT_MATCH_PATTERN": 422,
    "INVALID_AGE_RANGE": 422,
    "INVALID_VALIDITY_RANGE": 422,
    "INVALID_IDENTIFICATION_NUMBER": 422,
    "BIRTH_DATE_REQUIRED": 422,
    "AGE_OUT_OF_RANGE": 422,
    "BIRTH_DATE_IN_FUTURE": 422,
    "COUNTRY_NOT_FOUND": 422,
    "DUPLICATE_IDENTIFICATION": 409,
    "DUPLICATE_ACTIVE_RULE": 409,
    "VERSION_CONFLICT": 409,
    "INVALID_STATUS_TRANSITION": 409,
    "DEPENDENCY_UNAVAILABLE": 503,
}

_HTTP_CODES = {
    400: ("MALFORMED_REQUEST", "Solicitud mal formada"),
    401: ("UNAUTHENTICATED", "No autenticado"),
    403: ("FORBIDDEN", "Acceso denegado"),
    404: ("NOT_FOUND", "Recurso no encontrado"),
    405: ("METHOD_NOT_ALLOWED", "Método no permitido"),
}


def status_for_code(code: str) -> int | None:
    """Estado HTTP de un `code` de aplicación, o `None` si no está mapeado."""
    return _STATUS_BY_CODE.get(code)


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


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = [str(part) for part in loc[1:]] if len(loc) > 1 else [str(part) for part in loc]
    return ".".join(parts)


async def _handle_application_error(
    request: Request,
    exc: PartyIdentityError,
) -> JSONResponse:
    status = status_for_code(exc.code)

    if status is None:
        logger.error("Código de error sin estado HTTP asignado: %s", exc.code)
        return problem_response(
            request,
            status=500,
            code="INTERNAL_ERROR",
            title="Error interno",
            detail="Ocurrió un error inesperado. Informe el trace_id al soporte.",
        )

    return problem_response(
        request,
        status=status,
        code=exc.code,
        title=exc.title,
        detail=exc.message,
        extra=exc.context or None,
    )


async def _handle_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()

    if any(error.get("type") == "json_invalid" for error in errors):
        return problem_response(
            request,
            status=400,
            code="MALFORMED_REQUEST",
            title="Solicitud mal formada",
            detail="El cuerpo de la solicitud no es un JSON válido.",
        )

    return problem_response(
        request,
        status=422,
        code="VALIDATION_ERROR",
        title="Solicitud inválida",
        detail="La solicitud contiene datos inválidos.",
        extra={
            "errors": [
                {
                    "field": _field_name(tuple(error.get("loc", ()))),
                    "message": error.get("msg", ""),
                    "code": "VALIDATION_ERROR",
                }
                for error in errors
            ]
        },
    )


async def _handle_http_exception(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
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


def register_error_handlers(app: FastAPI) -> None:
    """Registra los manejadores de errores en la aplicación."""
    app.add_exception_handler(PartyIdentityError, _handle_application_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
