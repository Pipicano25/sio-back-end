from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


PUBLIC_API_PATHS = {
    "/health/live",
    "/health/ready",
}


def configure_openapi(app: FastAPI) -> None:
    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        components = schema.setdefault(
            "components",
            {},
        )

        security_schemes = components.setdefault(
            "securitySchemes",
            {},
        )

        security_schemes["bearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "Ingrese un Access Token válido emitido "
                "para acceder a los recursos protegidos."
            ),
        }

        schema["security"] = [
            {
                "bearerAuth": [],
            }
        ]

        paths = schema.get("paths", {})

        for public_path in PUBLIC_API_PATHS:
            path_item = paths.get(public_path)

            if path_item is None:
                continue

            for operation in path_item.values():
                if isinstance(operation, dict):
                    operation["security"] = []

        app.openapi_schema = schema

        return schema

    app.openapi = custom_openapi