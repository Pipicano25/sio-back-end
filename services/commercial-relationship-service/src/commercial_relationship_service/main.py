"""Punto de entrada de Commercial Relationship Service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, fields

from fastapi import Depends, FastAPI, Request
from sio_auth import SIOAuth, install_cors
from sio_contract_read import ContractReadSettings, create_contract_engine
from sqlalchemy import Engine

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
from commercial_relationship_service.infrastructure.contract_operational_context import (
    ContractCompanyAccessDirectory,
    ContractCompanyDirectory,
)
from commercial_relationship_service.infrastructure.contract_party_identity import ContractPartyDirectory
from commercial_relationship_service.infrastructure.contract_payment_reference import (
    ContractPaymentReferenceDirectory,
)
from commercial_relationship_service.infrastructure.contract_product_catalog import ContractProductCatalogDirectory
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


@dataclass(frozen=True, slots=True)
class ContractEngines:
    """Motores de lectura por vistas de contrato (spec 025, D27); `None` = ese propietario se lee por HTTP."""

    operational_context: Engine | None = None
    party_identity: Engine | None = None
    product_catalog: Engine | None = None
    payment_reference: Engine | None = None

    def dispose(self) -> None:
        for item in fields(self):
            engine = getattr(self, item.name)
            if engine is not None:
                engine.dispose()


def _engine(reads: ContractReadSettings | None) -> Engine | None:
    if reads is None or not reads.uses_contract:
        return None
    return create_contract_engine(reads, application_name="commercial-relationship-service")


def build_contract_engines(settings: Settings) -> ContractEngines:
    """Un motor por propietario con `<PROPIETARIO>_READ_SOURCE=contract`."""
    return ContractEngines(
        operational_context=_engine(settings.operational_context_reads),
        party_identity=_engine(settings.party_identity_reads),
        product_catalog=_engine(settings.product_catalog_reads),
        payment_reference=_engine(settings.payment_reference_reads),
    )


def _claims(request: Request):
    """`TokenClaims` que `sio-auth` dejó en la solicitud (token del usuario, FR-037)."""
    return getattr(request.state, "sio_claims", None)


def build_access_directory_factory(settings: Settings, contract_engine: Engine | None = None) -> AccessDirectoryFactory:
    """Operational Context `operational-access` y `me/operational-context` (vía propia, token del usuario, R-02).

    Con `contract_engine` (spec 025, `OPERATIONAL_CONTEXT_READ_SOURCE=contract`) el acceso y las membresías del
    resumen se leen de las vistas de contrato.
    """

    def factory(request: Request) -> HTTPCompanyAccessDirectory | ContractCompanyAccessDirectory:
        if contract_engine is not None:
            return ContractCompanyAccessDirectory(engine=contract_engine, claims=_claims(request))
        return HTTPCompanyAccessDirectory(
            base_url=settings.operational_context_base_url,
            authorization=request.headers.get("authorization"),
            timeout_seconds=settings.operational_context_timeout_seconds,
        )

    return factory


def build_company_directory_factory(
    settings: Settings, contract_engine: Engine | None = None
) -> CompanyDirectoryFactory:
    """Operational Context `companies/{id}` (token del usuario, R-07); con `contract_engine`, `v1_companies`."""

    def factory(request: Request) -> HTTPCompanyDirectory | ContractCompanyDirectory:
        if contract_engine is not None:
            return ContractCompanyDirectory(engine=contract_engine, claims=_claims(request))
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
    settings: Settings, token_client: KeycloakTokenClient, contract_engine: Engine | None = None
) -> ProductDirectoryFactory:
    """Product Catalog con la identidad técnica propia (R-05).

    Con `contract_engine` (spec 025, `PRODUCT_CATALOG_READ_SOURCE=contract`) la unidad base se lee de `v1_products`;
    la elegibilidad (`batch-lookup`) y el primer uso siguen por HTTP (FR-036).
    """
    http_directory = HTTPProductCatalogDirectory(
        base_url=settings.product_catalog_base_url,
        timeout_seconds=settings.product_catalog_timeout_seconds,
        token_client=token_client,
    )
    directory: HTTPProductCatalogDirectory | ContractProductCatalogDirectory = (
        http_directory
        if contract_engine is None
        else ContractProductCatalogDirectory(engine=contract_engine, http=http_directory)
    )

    def factory(request: Request) -> HTTPProductCatalogDirectory | ContractProductCatalogDirectory:
        return directory

    return factory


def build_payment_directory_factory(
    settings: Settings, token_client: KeycloakTokenClient, contract_engine: Engine | None = None
) -> PaymentDirectoryFactory:
    """Payment Reference con la identidad técnica propia (DS-02, R-08).

    Con `contract_engine` (spec 025, `PAYMENT_REFERENCE_READ_SOURCE=contract`) el tipo de condición se lee de
    `v1_payment_condition_types`.
    """
    directory: HTTPPaymentReferenceDirectory | ContractPaymentReferenceDirectory
    if contract_engine is not None:
        directory = ContractPaymentReferenceDirectory(engine=contract_engine)
    else:
        directory = HTTPPaymentReferenceDirectory(
            base_url=settings.payment_reference_base_url,
            timeout_seconds=settings.payment_reference_timeout_seconds,
            token_client=token_client,
        )

    def factory(request: Request) -> HTTPPaymentReferenceDirectory | ContractPaymentReferenceDirectory:
        return directory

    return factory


def build_party_directory_factory(settings: Settings, contract_engine: Engine | None = None) -> PartyDirectoryFactory:
    """Party Identity con el token del usuario (DS-04).

    Con `contract_engine` (spec 025, `PARTY_IDENTITY_READ_SOURCE=contract`) se leen sus vistas de contrato con el
    permiso del token.
    """

    def factory(request: Request) -> HTTPPartyDirectory | ContractPartyDirectory:
        if contract_engine is not None:
            return ContractPartyDirectory(engine=contract_engine, claims=_claims(request))
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
    # Spec 025 (D27): cada propietario con `<PROPIETARIO>_READ_SOURCE=contract` se lee de sus vistas de contrato.
    engines = build_contract_engines(current_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        database.dispose()
        engines.dispose()

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
        current_settings, engines.operational_context
    )
    app.state.company_directory_factory = company_directory_factory or build_company_directory_factory(
        current_settings, engines.operational_context
    )
    token_client = build_token_client(current_settings)
    app.state.product_directory_factory = (
        product_directory_factory
        or build_product_directory_factory(current_settings, token_client, engines.product_catalog)
    )
    app.state.payment_directory_factory = (
        payment_directory_factory
        or build_payment_directory_factory(current_settings, token_client, engines.payment_reference)
    )
    app.state.party_directory_factory = party_directory_factory or build_party_directory_factory(
        current_settings, engines.party_identity
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
