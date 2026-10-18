"""Configuración OpenAPI de business-reporting-service."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

TAG_REPORTS = "Reportes"

OPENAPI_TAGS = [
    {"name": "health"},
    {
        "name": TAG_REPORTS,
        "description": (
            "Reportes de **solo lectura**, generados bajo demanda en JSON o CSV (`format=csv`, UTF-8 con BOM). Las "
            "agregaciones las calculan Sales, Purchase e Inventory; este servicio las consulta **con el token del "
            "usuario**, así que además del permiso del reporte se necesita el de lectura del propietario. Exigen "
            "membresía `ACTIVE` en la empresa; cualquier sucursal de la empresa se puede leer. Período de hasta 366 "
            "días. Un CSV completo termina con la fila `TOTAL FILAS`. Sin costos ni márgenes en esta fase."
        ),
    },
]

PROBLEM = {"application/problem+json": {"schema": {"type": "object"}}}

_USER_RESPONSES = {
    "401": "Sin token o token inválido: `BUSINESS_REPORTING.UNAUTHENTICATED`.",
    "503": (
        "`BUSINESS_REPORTING.DEPENDENCY_UNAVAILABLE`: una dependencia no respondió a tiempo, respondió algo inválido "
        "o hubo un incidente de integridad. Nunca hay reportes parciales; la dependencia solo se registra en el log."
    ),
}


def problem(description: str) -> dict[str, Any]:
    return {"description": description, "content": PROBLEM}


REPORT_ERRORS = {
    "403": problem("`BUSINESS_REPORTING.FORBIDDEN`: sin el permiso del reporte o sin el de lectura del propietario."),
    "404": problem("`BUSINESS_REPORTING.NOT_FOUND`: empresa inexistente, sin membresía `ACTIVE` o sucursal de otra empresa."),
    "422": problem("`BUSINESS_REPORTING.VALIDATION_ERROR`: fechas, período, parámetros o máximo de filas del CSV."),
}


def configure_bearer_openapi(app: FastAPI, public_paths: Collection[str]) -> None:
    """Documenta HTTP Bearer en OpenAPI; la validación real la hace `sio-auth`."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title, version=app.version, description=app.description, routes=app.routes, tags=app.openapi_tags
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
                        operation["responses"].setdefault(status_code, {"description": description, "content": PROBLEM})

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
