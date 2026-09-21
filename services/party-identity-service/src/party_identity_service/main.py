"""Punto de entrada de Party Identity Service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from party_identity_service.api.health import build_router as build_health_router
from party_identity_service.api.openapi import configure_bearer_openapi
from party_identity_service.api.person_identities import (
    build_router as build_person_identities_router,
)
from party_identity_service.api.security import build_auth
from party_identity_service.config import Settings, load_settings
from party_identity_service.infrastructure.database import Database

SERVICE_TITLE = "SIO Party Identity Service"
SERVICE_VERSION = "0.1.0"

HEALTH_PUBLIC_PATHS = {
    "/health/live",
    "/health/ready",
}

DOCS_PUBLIC_PATHS = {
    "/docs",
    "/openapi.json",
}


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construye la aplicación FastAPI del microservicio.

    Args:
        settings: Configuración opcional. Cuando no se proporciona se
            obtiene desde variables de entorno.

    Returns:
        Aplicación FastAPI configurada con health checks, OpenAPI y
        protección global mediante `sio-auth`.
    """
    current_settings = settings or load_settings()
    database = Database(
        current_settings.database_url,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Administra recursos compartidos durante la vida de la app.

        Args:
            app: Aplicación FastAPI en ejecución.
        """
        app.state.settings = current_settings
        app.state.database = database

        yield

        database.dispose()

    app = FastAPI(
        title=SERVICE_TITLE,
        description=(
            "Microservicio responsable de las identidades globales "
            "de personas y organizaciones de SIO."
        ),
        version=SERVICE_VERSION,
        docs_url="/docs" if current_settings.docs_enabled else None,
        redoc_url=None,
        openapi_url=(
            "/openapi.json"
            if current_settings.docs_enabled
            else None
        ),
        lifespan=lifespan,
    )

    public_paths = set(HEALTH_PUBLIC_PATHS)

    if current_settings.docs_enabled:
        public_paths.update(DOCS_PUBLIC_PATHS)

        configure_bearer_openapi(
            app=app,
            public_paths=public_paths,
        )

    auth = build_auth()

    app.include_router(
        build_health_router(
            database,
        )
    )

    app.include_router(
        build_person_identities_router(
            auth,
        )
    )

    auth.protect(
        app,
        public_paths=public_paths,
    )

    return app


app = create_app()
