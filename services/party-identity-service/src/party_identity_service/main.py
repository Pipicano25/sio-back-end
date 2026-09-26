"""Punto de entrada de Party Identity Service."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sio_auth import SIOAuth

from party_identity_service.api.dependencies import CountryDirectoryFactory
from party_identity_service.api.errors import register_error_handlers
from party_identity_service.api.health import build_router as build_health_router
from party_identity_service.api.identification_type_rules import (
    build_router as build_identification_type_rules_router,
)
from party_identity_service.api.openapi import configure_bearer_openapi
from party_identity_service.api.organization_identities import (
    build_router as build_organization_identities_router,
)
from party_identity_service.api.person_identities import (
    build_router as build_person_identities_router,
)
from party_identity_service.api.security import build_auth
from party_identity_service.api.tracing import TracingMiddleware
from party_identity_service.config import Settings, load_settings
from party_identity_service.infrastructure.database import Database
from party_identity_service.infrastructure.geography_country_validator import (
    HTTPGeographyCountryValidator,
)
from party_identity_service.observability import configure_logging

SERVICE_TITLE = "SIO Party Identity Service"
SERVICE_VERSION = "0.2.0"
API_PREFIX = "/api/v1"

HEALTH_PUBLIC_PATHS = {
    "/health/live",
    "/health/ready",
}

DOCS_PUBLIC_PATHS = {
    "/docs",
    "/openapi.json",
}


def build_country_directory_factory(settings: Settings) -> CountryDirectoryFactory:
    """Fábrica del adaptador HTTP de Geography, único camino productivo (FR-044).

    Propaga el token del usuario de la solicitud (D5).
    """

    def factory(request: Request) -> HTTPGeographyCountryValidator:
        return HTTPGeographyCountryValidator(
            base_url=settings.geography_service_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=settings.geography_timeout_seconds,
        )

    return factory


def create_app(
    settings: Settings | None = None,
    *,
    auth: SIOAuth | None = None,
    country_directory_factory: CountryDirectoryFactory | None = None,
) -> FastAPI:
    """Construye la aplicación FastAPI del microservicio.

    Args:
        settings: Configuración opcional; por defecto se lee del entorno.
        auth: Fachada `sio-auth` opcional (las pruebas inyectan una con JWKS
            local).
        country_directory_factory: Fábrica opcional del puerto de Geography.
            Solo las pruebas la inyectan; si se omite, se usa siempre el
            adaptador HTTP real.

    Returns:
        Aplicación FastAPI con salud, API `/api/v1`, errores RFC 9457,
        trazabilidad y protección global mediante `sio-auth`.
    """
    current_settings = settings or load_settings()
    configure_logging()
    database = Database(current_settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Libera el pool de conexiones al detener la aplicación."""
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

    app.state.settings = current_settings
    app.state.database = database
    app.state.country_directory_factory = (
        country_directory_factory
        or build_country_directory_factory(current_settings)
    )

    public_paths = set(HEALTH_PUBLIC_PATHS)

    if current_settings.docs_enabled:
        public_paths.update(DOCS_PUBLIC_PATHS)
        configure_bearer_openapi(
            app=app,
            public_paths=public_paths,
        )

    current_auth = auth or build_auth()

    register_error_handlers(app)
    app.include_router(build_health_router(database))
    app.include_router(
        build_person_identities_router(current_auth),
        prefix=API_PREFIX,
    )
    app.include_router(
        build_organization_identities_router(current_auth),
        prefix=API_PREFIX,
    )
    app.include_router(
        build_identification_type_rules_router(current_auth),
        prefix=API_PREFIX,
    )

    current_auth.protect(
        app,
        public_paths=public_paths,
    )
    # Último middleware agregado = más externo: envuelve también a sio-auth.
    app.add_middleware(TracingMiddleware)

    return app


app = create_app()
