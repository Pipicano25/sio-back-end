"""Configuración OpenAPI de Operational Context Service."""

from collections.abc import Collection
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def configure_bearer_openapi(
    app: FastAPI,
    public_paths: Collection[str],
) -> None:
    """Configura autenticación HTTP Bearer en OpenAPI.

    Esta configuración documenta el mecanismo Bearer para Swagger. La
    validación real del token continúa delegada en `sio-auth`.

    Args:
        app: Aplicación FastAPI.
        public_paths: Rutas públicas que no requieren Bearer.
    """

    def custom_openapi() -> dict[str, Any]:
        """Construye el esquema OpenAPI del servicio.

        Returns:
            Esquema OpenAPI con seguridad HTTP Bearer.
        """
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        components = schema.setdefault("components", {})
        security_schemes = components.setdefault(
            "securitySchemes",
            {},
        )

        security_schemes["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Ingrese un Access Token válido emitido para SIO."
            ),
        }

        paths = schema.get("paths", {})

        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            for operation in path_item.values():
                if not isinstance(operation, dict):
                    continue

                if "responses" not in operation:
                    continue

                if path in public_paths:
                    operation["security"] = []
                else:
                    operation["security"] = [{"BearerAuth": []}]

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
