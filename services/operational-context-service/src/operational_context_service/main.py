"""Punto de entrada de Operational Context Service."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sio_auth import SIOAuth

from operational_context_service.api.advisor_assignments import build_router as build_advisors_router
from operational_context_service.api.application_users import (
    build_router as build_application_users_router,
)
from operational_context_service.api.branches import build_router as build_branches_router
from operational_context_service.api.companies import build_router as build_companies_router
from operational_context_service.api.dependencies import (
    AccountDirectoryFactory,
    GeographyDirectoryFactory,
    OrganizationDirectoryFactory,
    PersonDirectoryFactory,
)
from operational_context_service.api.errors import register_error_handlers
from operational_context_service.api.health import build_router as build_health_router
from operational_context_service.api.openapi import configure_bearer_openapi
from operational_context_service.api.operational_access import build_router as build_operational_access_router
from operational_context_service.api.security import build_auth
from operational_context_service.api.tracing import TracingMiddleware
from operational_context_service.api.user_branches import build_router as build_user_branches_router
from operational_context_service.config import Settings, load_settings
from operational_context_service.infrastructure.database import Database
from operational_context_service.infrastructure.geography_directory import HTTPGeographyDirectory
from operational_context_service.infrastructure.keycloak_account_directory import (
    KeycloakAccountDirectory,
)
from operational_context_service.infrastructure.keycloak_token_client import KeycloakTokenClient
from operational_context_service.infrastructure.party_identity_organization_directory import (
    HTTPPartyIdentityOrganizationDirectory,
)
from operational_context_service.infrastructure.party_identity_person_directory import (
    HTTPPartyIdentityPersonDirectory,
)
from operational_context_service.observability import configure_logging

SERVICE_TITLE = "SIO Operational Context Service"
SERVICE_VERSION = "0.1.0"
API_PREFIX = "/api/v1"

HEALTH_PUBLIC_PATHS = {"/health/live", "/health/ready"}
DOCS_PUBLIC_PATHS = {"/docs", "/openapi.json"}


def build_organization_directory_factory(settings: Settings) -> OrganizationDirectoryFactory:
    """Adaptador HTTP de Party Identity: único camino productivo (R-12).

    Propaga el token del usuario de la solicitud (D5).
    """

    def factory(request: Request) -> HTTPPartyIdentityOrganizationDirectory:
        return HTTPPartyIdentityOrganizationDirectory(
            base_url=settings.party_identity_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=settings.party_identity_timeout_seconds,
        )

    return factory


def build_geography_directory_factory(settings: Settings) -> GeographyDirectoryFactory:
    """Adaptador HTTP de Geography: único camino productivo (R-12)."""

    def factory(request: Request) -> HTTPGeographyDirectory:
        return HTTPGeographyDirectory(
            base_url=settings.geography_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=settings.geography_timeout_seconds,
        )

    return factory


def build_person_directory_factory(settings: Settings) -> PersonDirectoryFactory:
    """Adaptador HTTP de personas en Party Identity; propaga el token del usuario (D5, R-08)."""

    def factory(request: Request) -> HTTPPartyIdentityPersonDirectory:
        return HTTPPartyIdentityPersonDirectory(
            base_url=settings.party_identity_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=settings.party_identity_timeout_seconds,
        )

    return factory


def build_account_directory_factory(settings: Settings) -> AccountDirectoryFactory:
    """Adaptador de la Admin API de Keycloak con el cliente técnico propio (R-06, DS-14).

    Una sola instancia por proceso para reutilizar el token técnico y el UUID
    del cliente `sio-api`. No llama a Keycloak al arrancar.
    """
    token_client = KeycloakTokenClient(
        base_url=settings.keycloak_base_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_client_id,
        client_secret=settings.keycloak_client_secret,
        timeout_seconds=settings.keycloak_timeout_seconds,
    )
    directory = KeycloakAccountDirectory(
        base_url=settings.keycloak_base_url,
        realm=settings.keycloak_realm,
        sio_api_client_id=settings.sio_api_client_id,
        timeout_seconds=settings.keycloak_timeout_seconds,
        token_client=token_client,
    )

    def factory(request: Request) -> KeycloakAccountDirectory:
        return directory

    return factory


def create_app(
    settings: Settings | None = None,
    *,
    auth: SIOAuth | None = None,
    organization_directory_factory: OrganizationDirectoryFactory | None = None,
    geography_directory_factory: GeographyDirectoryFactory | None = None,
    person_directory_factory: PersonDirectoryFactory | None = None,
    account_directory_factory: AccountDirectoryFactory | None = None,
) -> FastAPI:
    """Construye la aplicación FastAPI del microservicio.

    Args:
        settings: Configuración opcional; por defecto se lee del entorno.
        auth: Fachada `sio-auth` opcional (las pruebas inyectan una con JWKS local).
        organization_directory_factory: Fábrica del puerto de Party Identity. Solo
            las pruebas la inyectan; si se omite, se usa siempre el adaptador HTTP.
        geography_directory_factory: Ídem para Geography.
        person_directory_factory: Ídem para personas de Party Identity (Fase B).
        account_directory_factory: Ídem para la Admin API de Keycloak (Fase B).
    """
    current_settings = settings or load_settings()
    configure_logging()
    database = Database(current_settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        database.dispose()

    app = FastAPI(
        title=SERVICE_TITLE,
        description=(
            "Microservicio responsable del contexto operativo de SIO: empresas "
            "cliente de la plataforma y sus sucursales."
        ),
        version=SERVICE_VERSION,
        docs_url="/docs" if current_settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if current_settings.docs_enabled else None,
        lifespan=lifespan,
    )

    app.state.settings = current_settings
    app.state.database = database
    app.state.organization_directory_factory = (
        organization_directory_factory or build_organization_directory_factory(current_settings)
    )
    app.state.geography_directory_factory = (
        geography_directory_factory or build_geography_directory_factory(current_settings)
    )
    app.state.person_directory_factory = (
        person_directory_factory or build_person_directory_factory(current_settings)
    )
    app.state.account_directory_factory = (
        account_directory_factory or build_account_directory_factory(current_settings)
    )

    public_paths = set(HEALTH_PUBLIC_PATHS)

    if current_settings.docs_enabled:
        public_paths.update(DOCS_PUBLIC_PATHS)
        configure_bearer_openapi(app=app, public_paths=public_paths)

    current_auth = auth or build_auth()

    register_error_handlers(app)
    app.include_router(build_health_router(database))
    app.include_router(build_companies_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_branches_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_application_users_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_user_branches_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_advisors_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_operational_access_router(current_auth), prefix=API_PREFIX)

    current_auth.protect(app, public_paths=public_paths)
    # Último middleware agregado = más externo: envuelve también a sio-auth.
    app.add_middleware(TracingMiddleware)

    return app


app = create_app()
