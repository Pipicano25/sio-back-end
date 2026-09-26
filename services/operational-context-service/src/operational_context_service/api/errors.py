"""Traducción de errores a Problem Details (RFC 9457) con `code` y `trace_id` (D3).

Este módulo es el **único** que asigna estados HTTP (Principio XII): las
excepciones de aplicación solo llevan `code`, mensaje y campo, y la tabla
`_STATUS_BY_CODE` los traduce.

Regla D11 provisional (`contracts/errors.md`): `400` solo si el cuerpo JSON no
se puede interpretar; `422` para validación de entrada y de dominio, incluidas
las referencias externas inexistentes, inactivas o incoherentes; `409`
unicidad, versión y transición; `404` recurso de la ruta inexistente o fuera
del alcance del usuario (DS-06); `503` dependencia no disponible, con la
extensión `dependency` (C-13).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from operational_context_service.application.exceptions import (
    DependencyUnavailableError,
    OperationalContextError,
)
from operational_context_service.observability import SERVICE_LOGGER

CODE_PREFIX = "OPERATIONAL_CONTEXT."
ERROR_TYPE_BASE = "https://sio/errors/operational-context"
PROBLEM_MEDIA_TYPE = "application/problem+json"

logger = logging.getLogger(SERVICE_LOGGER)

_STATUS_BY_CODE: dict[str, int] = {
    "NOT_FOUND": 404,
    "VALIDATION_ERROR": 422,
    "IMMUTABLE_FIELD": 422,
    "COMPANY_INACTIVE": 422,
    "ORGANIZATION_IDENTITY_NOT_FOUND": 422,
    "ORGANIZATION_IDENTITY_INACTIVE": 422,
    "GEOGRAPHY_PARENT_REQUIRED": 422,
    "COUNTRY_NOT_FOUND": 422,
    "ADMINISTRATIVE_DIVISION_NOT_FOUND": 422,
    "CITY_NOT_FOUND": 422,
    "LOCATION_INACTIVE": 422,
    "GEOGRAPHY_INCOHERENT": 422,
    "DUPLICATE_ORGANIZATION_IDENTITY": 409,
    "DUPLICATE_BRANCH_CODE": 409,
    "VERSION_CONFLICT": 409,
    "INVALID_STATUS_TRANSITION": 409,
    "DEPENDENCY_UNAVAILABLE": 503,
    # Fase B (specs/005-operational-context-users/contracts/errors.md).
    "KEYCLOAK_USER_NOT_FOUND": 422,
    "KEYCLOAK_USER_DISABLED": 422,
    "TECHNICAL_ACCOUNT_NOT_ALLOWED": 422,
    "PERSON_IDENTITY_NOT_FOUND": 422,
    "PERSON_IDENTITY_INACTIVE": 422,
    "MEMBERSHIP_INACTIVE": 422,
    "BRANCH_INACTIVE": 422,
    "BRANCH_COMPANY_MISMATCH": 422,
    "INVALID_VALIDITY_PERIOD": 422,
    "DUPLICATE_MEMBERSHIP": 409,
    "DUPLICATE_USER_BRANCH": 409,
    "PRIMARY_ADVISOR_EXISTS": 409,
    "DUPLICATE_ADVISOR_ASSIGNMENT": 409,
    "NO_ACTIVE_PRIMARY_ADVISOR": 409,
    "PRIMARY_ADVISOR_MISMATCH": 409,
    # Capacidad `platform:lookup` exigida de forma condicional (FR-045).
    "FORBIDDEN": 403,
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
    exc: OperationalContextError,
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

    if isinstance(exc, DependencyUnavailableError):
        # La causa real queda en el log con el trace_id; nunca en la respuesta (R-03).
        logger.warning(
            "Dependencia no disponible proveedor=%s operacion=%s causa=%s",
            exc.provider,
            exc.operation,
            exc.cause,
        )

    extra: dict[str, Any] = dict(exc.context)

    if isinstance(exc, DependencyUnavailableError):
        # Extensión estable que identifica la dependencia sin cambiar el `code`
        # publicado (C-13): party-identity, geography o keycloak.
        extra["dependency"] = exc.provider

    if exc.field:
        extra["errors"] = [
            {"field": exc.field, "message": exc.message, "code": exc.code},
        ]

    return problem_response(
        request,
        status=status,
        code=exc.code,
        title=exc.title,
        detail=exc.message,
        extra=extra or None,
    )


def _validation_message(error: dict[str, Any]) -> str:
    message = str(error.get("msg", ""))
    # Pydantic antepone "Value error, " a los ValueError de los validadores.
    return message.removeprefix("Value error, ")


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
                    "message": _validation_message(error),
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
    app.add_exception_handler(OperationalContextError, _handle_application_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
