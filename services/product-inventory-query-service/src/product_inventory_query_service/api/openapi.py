"""Configuración OpenAPI de product-inventory-query-service."""

from __future__ import annotations

from collections.abc import Collection
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

TAG_QUERIES = "Consultas consolidadas"

OPENAPI_TAGS = [
    {"name": "health"},
    {
        "name": TAG_QUERIES,
        "description": (
            "Consultas de **solo lectura** de productos, inventario, bajo stock y resumen de una empresa, compuestas "
            "desde Commercial Relationship, Product Catalog, Inventory y Operational Context. Exigen membresía "
            "`ACTIVE` en la empresa; cualquier sucursal de la empresa se puede leer. Los listados se paginan por "
            "cursor (sin totales) con `page_size` de 1 a 20. Nunca se entregan costos."
        ),
    },
]

PROBLEM = {"application/problem+json": {"schema": {"type": "object"}}}

_USER_RESPONSES = {
    "401": "Sin token o token inválido: `PRODUCT_INVENTORY_QUERY.UNAUTHENTICATED`.",
    "503": (
        "`PRODUCT_INVENTORY_QUERY.DEPENDENCY_UNAVAILABLE`: una dependencia no respondió a tiempo o respondió algo "
        "inválido. Nunca hay resultados parciales; la dependencia solo se registra en el log."
    ),
}


def problem(description: str) -> dict[str, Any]:
    return {"description": description, "content": PROBLEM}


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
