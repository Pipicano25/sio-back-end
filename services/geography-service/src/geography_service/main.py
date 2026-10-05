from contextlib import asynccontextmanager

from fastapi import FastAPI
from sio_auth import SIOAuth

from geography_service.api.errors import register_database_unavailable_handler
from geography_service.api.global_countries import (
    build_router as build_global_countries_router,
)
from geography_service.api.health import (
    build_router as build_health_router,
)
from geography_service.api.openapi import configure_openapi
from geography_service.config import Settings
from geography_service.infrastructure.database import Database
from geography_service.api.global_administrative_divisions import (
    build_router as build_global_administrative_divisions_router,
)
from geography_service.api.global_cities import (
    build_router as build_global_cities_router,
)


PUBLIC_PATHS = {
    "/health/live",
    "/health/ready",
}


def create_app() -> FastAPI:
    """Construye y configura la aplicación FastAPI.

    Returns:
        Aplicación FastAPI completamente configurada con seguridad,
        health checks y routers de negocio.
    """
    settings = Settings.from_env()

    database = Database(
        settings.database_url,
    )

    auth = SIOAuth.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.database = database

        yield

        database.dispose()

    app = FastAPI(
        title="SIO Geography Service",
        description=(
            "Microservicio encargado de los catálogos "
            "geográficos globales de SIO."
        ),
        version="0.1.0",
        docs_url=(
            "/docs"
            if settings.docs_enabled
            else None
        ),
        redoc_url=None,
        openapi_url=(
            "/openapi.json"
            if settings.docs_enabled
            else None
        ),
        lifespan=lifespan,
    )

    register_database_unavailable_handler(app)

    app.include_router(
        build_health_router(
            database,
        )
    )

    app.include_router(
        build_global_countries_router(
            auth,
        )
    )

    app.include_router(
        build_global_administrative_divisions_router(auth),
    )

    app.include_router(
        build_global_cities_router(
            auth,
        )
    )

    public_paths = set(
        PUBLIC_PATHS,
    )

    if settings.docs_enabled:
        public_paths.update(
            {
                "/docs",
                "/openapi.json",
            }
        )

        configure_openapi(
            app,
        )

    auth.protect(
        app,
        public_paths=public_paths,
    )

    return app


app = create_app()