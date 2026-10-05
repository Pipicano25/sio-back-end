"""Punto de entrada de Payment Reference Service."""

from fastapi import FastAPI
from sio_auth import SIOAuth

from payment_reference_service.api.errors import register_error_handlers
from payment_reference_service.api.global_payment_condition_types import (
    router as global_payment_condition_types_router,
)
from payment_reference_service.api.health import router as health_router
from payment_reference_service.api.openapi import configure_bearer_openapi
from payment_reference_service.api.security import auth as default_auth
from payment_reference_service.config import Settings, load_settings
from payment_reference_service.api.global_payment_methods import (
    router as global_payment_methods_router,
)


SERVICE_TITLE = "Payment Reference Service"
SERVICE_VERSION = "0.1.0"

HEALTH_PUBLIC_PATHS = {
    "/health/live",
    "/health/ready",
}

DOCS_PUBLIC_PATHS = {
    "/docs",
    "/openapi.json",
}


def create_app(
    settings: Settings | None = None,
    *,
    auth: SIOAuth | None = None,
) -> FastAPI:
    """Construye la aplicación FastAPI del microservicio.

    Args:
        settings: Configuración opcional. Cuando no se proporciona se
            obtiene desde variables de entorno.
        auth: Solo para pruebas: instancia de `SIOAuth` con un JWKS de
            prueba. Cuando es `None` se usa la autenticación real
            (`SIOAuth.from_env()`); no existe ninguna vía para desactivar
            la protección de las rutas.

    Returns:
        Aplicación FastAPI configurada.
    """
    current_settings = settings or load_settings()
    current_auth = auth if auth is not None else default_auth

    app = FastAPI(
        title=SERVICE_TITLE,
        version=SERVICE_VERSION,
        docs_url="/docs" if current_settings.docs_enabled else None,
        redoc_url=None,
        openapi_url=(
            "/openapi.json"
            if current_settings.docs_enabled
            else None
        ),
    )

    register_error_handlers(app)

    app.include_router(health_router)
    app.include_router(global_payment_condition_types_router)
    app.include_router(global_payment_methods_router)

    public_paths = set(HEALTH_PUBLIC_PATHS)

    if current_settings.docs_enabled:
        public_paths.update(DOCS_PUBLIC_PATHS)

        configure_bearer_openapi(
            app=app,
            public_paths=public_paths,
        )

    current_auth.protect(
        app,
        public_paths=public_paths,
    )

    return app


def app_factory() -> FastAPI:
    """Construye la aplicación utilizando el entorno actual.

    Returns:
        Aplicación FastAPI configurada.
    """
    return create_app()
