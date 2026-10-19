"""Punto de entrada de Commercial Relationship Service."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from sio_auth import SIOAuth, install_cors

import commercial_relationship_service.application.audit_events  # noqa: F401  (registra la outbox de auditoría, feature 016)
from commercial_relationship_service.audit_context import bind_audit_actor
from commercial_relationship_service.api.applicable_prices import (
    build_router as build_applicable_prices_router,
)
from commercial_relationship_service.api.company_customers import (
    build_router as build_customers_router,
)
from commercial_relationship_service.api.company_product_presentations import (
    build_router as build_presentations_router,
)
from commercial_relationship_service.api.company_products import (
    build_router as build_products_router,
)
from commercial_relationship_service.api.company_summaries import (
    build_router as build_summaries_router,
)
from commercial_relationship_service.api.company_suppliers import (
    build_router as build_suppliers_router,
)
from commercial_relationship_service.api.dependencies import (
    AccessDirectoryFactory,
    CompanyDirectoryFactory,
    PartyDirectoryFactory,
    PaymentDirectoryFactory,
    ProductDirectoryFactory,
)
from commercial_relationship_service.api.errors import register_error_handlers
from commercial_relationship_service.api.health import build_router as build_health_router
from commercial_relationship_service.api.openapi import OPENAPI_TAGS, configure_bearer_openapi
from commercial_relationship_service.api.price_list_items import (
    build_router as build_price_list_items_router,
)
from commercial_relationship_service.api.price_lists import (
    build_router as build_price_lists_router,
)
from commercial_relationship_service.api.automatic_prices import (
    build_router as build_automatic_prices_router,
)
from commercial_relationship_service.api.company_product_taxes import (
    build_router as build_product_taxes_router,
)
from commercial_relationship_service.api.pricing_policies import (
    build_router as build_pricing_policies_router,
)
from commercial_relationship_service.api.security import build_auth
from commercial_relationship_service.api.supplier_payment_conditions import (
    build_router as build_payment_conditions_router,
)
from commercial_relationship_service.api.supplier_products import (
    build_router as build_supplier_products_router,
)
from commercial_relationship_service.api.tracing import TracingMiddleware
from commercial_relationship_service.config import Settings, load_settings
from commercial_relationship_service.infrastructure.database import Database
from commercial_relationship_service.infrastructure.keycloak_token_client import (
    KeycloakTokenClient,
)
from commercial_relationship_service.infrastructure.operational_context_directory import (
    HTTPCompanyAccessDirectory,
    HTTPCompanyDirectory,
)
from commercial_relationship_service.infrastructure.party_identity_directory import (
    HTTPPartyDirectory,
)
from commercial_relationship_service.infrastructure.payment_reference_directory import (
    HTTPPaymentReferenceDirectory,
)
from commercial_relationship_service.infrastructure.product_catalog_directory import (
    HTTPProductCatalogDirectory,
)
from commercial_relationship_service.observability import configure_logging

SERVICE_TITLE = "SIO Commercial Relationship Service"
SERVICE_VERSION = "0.1.0"
API_PREFIX = "/api/v1"

HEALTH_PUBLIC_PATHS = {"/health/live", "/health/ready"}
DOCS_PUBLIC_PATHS = {"/docs", "/openapi.json"}


def build_access_directory_factory(settings: Settings) -> AccessDirectoryFactory:
    """Operational Context `operational-access` (vía propia, token del usuario, R-02)."""

    def factory(request: Request) -> HTTPCompanyAccessDirectory:
        return HTTPCompanyAccessDirectory(
            base_url=settings.operational_context_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=settings.operational_context_timeout_seconds,
        )

    return factory


def build_company_directory_factory(settings: Settings) -> CompanyDirectoryFactory:
    """Operational Context `companies/{id}` (token del usuario, R-07)."""

    def factory(request: Request) -> HTTPCompanyDirectory:
        return HTTPCompanyDirectory(
            base_url=settings.operational_context_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=settings.operational_context_timeout_seconds,
        )

    return factory


def build_token_client(settings: Settings) -> KeycloakTokenClient:
    """Cliente `client_credentials` propio, compartido por Product Catalog y Payment Reference.

    Una sola instancia por proceso para reutilizar el token técnico. No llama a
    Keycloak al arrancar.
    """
    return KeycloakTokenClient(
        base_url=settings.keycloak_base_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_client_id,
        client_secret=settings.keycloak_client_secret,
        timeout_seconds=settings.keycloak_timeout_seconds,
    )


def build_product_directory_factory(
    settings: Settings, token_client: KeycloakTokenClient
) -> ProductDirectoryFactory:
    """Product Catalog con la identidad técnica propia (R-05)."""
    directory = HTTPProductCatalogDirectory(
        base_url=settings.product_catalog_base_url,
        timeout_seconds=settings.product_catalog_timeout_seconds,
        token_client=token_client,
    )

    def factory(request: Request) -> HTTPProductCatalogDirectory:
        return directory

    return factory


def build_payment_directory_factory(
    settings: Settings, token_client: KeycloakTokenClient
) -> PaymentDirectoryFactory:
    """Payment Reference con la identidad técnica propia (DS-02, R-08)."""
    directory = HTTPPaymentReferenceDirectory(
        base_url=settings.payment_reference_base_url,
        timeout_seconds=settings.payment_reference_timeout_seconds,
        token_client=token_client,
    )

    def factory(request: Request) -> HTTPPaymentReferenceDirectory:
        return directory

    return factory


def build_party_directory_factory(settings: Settings) -> PartyDirectoryFactory:
    """Party Identity con el token del usuario (DS-04)."""

    def factory(request: Request) -> HTTPPartyDirectory:
        return HTTPPartyDirectory(
            base_url=settings.party_identity_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=settings.party_identity_timeout_seconds,
        )

    return factory


def create_app(
    settings: Settings | None = None,
    *,
    auth: SIOAuth | None = None,
    access_directory_factory: AccessDirectoryFactory | None = None,
    company_directory_factory: CompanyDirectoryFactory | None = None,
    product_directory_factory: ProductDirectoryFactory | None = None,
    party_directory_factory: PartyDirectoryFactory | None = None,
    payment_directory_factory: PaymentDirectoryFactory | None = None,
) -> FastAPI:
    """Construye la aplicación FastAPI del microservicio.

    Las fábricas de puertos solo las inyectan las pruebas; si se omiten, se usan
    siempre los adaptadores HTTP reales (FR-050, sin modos por entorno).
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
            "Relación comercial privada de cada empresa: productos adoptados y sus "
            "presentaciones, clientes, proveedores, productos de proveedor, condiciones de pago "
            "y listas de precios."
        ),
        version=SERVICE_VERSION,
        # Autor de auditoría de la solicitud (feature 016): no agrega parámetros a ninguna ruta.
        dependencies=[Depends(bind_audit_actor)],
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs" if current_settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if current_settings.docs_enabled else None,
        lifespan=lifespan,
    )

    app.state.settings = current_settings
    app.state.database = database
    app.state.access_directory_factory = access_directory_factory or build_access_directory_factory(
        current_settings
    )
    app.state.company_directory_factory = (
        company_directory_factory or build_company_directory_factory(current_settings)
    )
    token_client = build_token_client(current_settings)
    app.state.product_directory_factory = (
        product_directory_factory or build_product_directory_factory(current_settings, token_client)
    )
    app.state.payment_directory_factory = (
        payment_directory_factory or build_payment_directory_factory(current_settings, token_client)
    )
    app.state.party_directory_factory = party_directory_factory or build_party_directory_factory(
        current_settings
    )

    public_paths = set(HEALTH_PUBLIC_PATHS)

    if current_settings.docs_enabled:
        public_paths.update(DOCS_PUBLIC_PATHS)
        configure_bearer_openapi(app=app, public_paths=public_paths)

    current_auth = auth or build_auth()

    register_error_handlers(app)
    app.include_router(build_health_router(database))
    app.include_router(build_products_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_product_taxes_router(current_auth), prefix=API_PREFIX)  # spec 021
    app.include_router(build_customers_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_suppliers_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_summaries_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_presentations_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_supplier_products_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_payment_conditions_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_price_lists_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_price_list_items_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_applicable_prices_router(current_auth), prefix=API_PREFIX)
    app.include_router(build_pricing_policies_router(current_auth), prefix=API_PREFIX)  # spec 021
    app.include_router(build_automatic_prices_router(current_auth), prefix=API_PREFIX)  # spec 021

    current_auth.protect(app, public_paths=public_paths)
    # Último middleware agregado = más externo: envuelve también a sio-auth.
    app.add_middleware(TracingMiddleware)
    # CORS abierto envuelve toda la pila, incluido el manejo de errores (sio-auth 0.5.0).
    install_cors(app)

    return app


app = create_app()
