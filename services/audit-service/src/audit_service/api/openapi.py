"""Configuración OpenAPI de Audit Service."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

TAG_REGISTRATION = "Registro de eventos (cuentas de servicio)"
TAG_COMPANY = "Auditoría de una empresa"
TAG_PLATFORM = "Auditoría de plataforma (eventos sin empresa)"

OPENAPI_TAGS = [
    {"name": "health"},
    {
        "name": TAG_REGISTRATION,
        "description": (
            "Los microservicios registran eventos de auditoría con su **identidad técnica** "
            "(`client_credentials`). Un token de usuario humano recibe `403` aunque tenga el "
            "permiso por comodín. Idempotente por `event_id`; los valores sensibles se ocultan "
            "con `\"***\"` y sus rutas quedan en `redacted_paths`."
        ),
    },
    {
        "name": TAG_COMPANY,
        "description": (
            "Consulta de los eventos **de una empresa**: exige `perm:audit:audit-events:read` y "
            "membresía `ACTIVE` del usuario en la empresa (validada en Operational Context con su "
            "token, que además exige `perm:operational-context:application_users:read`). Nunca "
            "devuelve eventos de plataforma."
        ),
    },
    {
        "name": TAG_PLATFORM,
        "description": (
            "Consulta de los eventos **sin empresa** (catálogos globales y otros recursos de "
            "plataforma): exige el permiso independiente `perm:audit:platform-events:read`, sin "
            "membresía. Nunca devuelve eventos de empresa."
        ),
    },
]

_PROBLEM = {"application/problem+json": {"schema": {"type": "object"}}}

# Respuestas transversales de toda ruta de usuario (`contracts/rest-api.md`, reglas generales).
_USER_RESPONSES = {
    "401": "Sin token o token inválido: `AUDIT.UNAUTHENTICATED`.",
    "403": "`AUDIT.FORBIDDEN`: falta el permiso de la operación (o, al registrar, no es una cuenta de servicio).",
    "503": (
        "`AUDIT.DEPENDENCY_UNAVAILABLE`: la extensión `dependency` indica cuál "
        "(`database`, `operational-context`)."
    ),
}


# Respuestas propias de grupos de rutas (`contracts/rest-api.md`, `contracts/errors.md`).
MALFORMED_BODY_RESPONSE = {
    400: {"description": "`AUDIT.MALFORMED_BODY`: el cuerpo no es JSON interpretable.", "content": _PROBLEM},
}
NOT_FOUND_RESPONSE = {
    404: {"description": "`AUDIT.NOT_FOUND`: evento inexistente o de otro alcance.", "content": _PROBLEM},
}
COMPANY_RESPONSES = {
    403: {
        "description": (
            "`AUDIT.FORBIDDEN`: falta `perm:audit:audit-events:read`; o "
            "`AUDIT.OPERATIONAL_ACCESS_DENIED`: Operational Context negó la evaluación de la membresía."
        ),
        "content": _PROBLEM,
    },
    404: {
        "description": "`AUDIT.NOT_FOUND`: empresa fuera del alcance del usuario o evento inexistente.",
        "content": _PROBLEM,
    },
}


def configure_bearer_openapi(app: FastAPI, public_paths: Collection[str]) -> None:
    """Documenta HTTP Bearer en OpenAPI; la validación real la hace `sio-auth`."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )

        components = schema.setdefault("components", {})
        components.setdefault("securitySchemes", {})["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Ingrese un Access Token válido emitido para SIO.",
        }

        for path, path_item in schema.get("paths", {}).items():
            if not isinstance(path_item, dict):
                continue

            for operation in path_item.values():
                if not isinstance(operation, dict) or "responses" not in operation:
                    continue

                if path in public_paths:
                    operation["security"] = []
                else:
                    operation["security"] = [{"BearerAuth": []}]
                    for status_code, description in _USER_RESPONSES.items():
                        operation["responses"].setdefault(
                            status_code, {"description": description, "content": _PROBLEM}
                        )

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
