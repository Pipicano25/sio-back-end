"""Construcción de los puertos de cada solicitud (Principio XV; spec 023, DR-07).

Todas las dependencias se consumen **con el token del usuario** de la solicitud: los adaptadores se crean por
solicitud sobre un cliente HTTP compartido por proveedor. Sin cliente técnico ni token propio. Las pruebas
inyectan en `create_app` una fábrica de puertos con dobles.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace

from fastapi import Request
from sio_auth.tokens import TokenClaims
from sio_contract_read import create_contract_engine

from business_reporting_service.application.exceptions import (
    COMMERCIAL_RELATIONSHIP,
    INVENTORY,
    OPERATIONAL_CONTEXT,
    PRODUCT_CATALOG,
    PURCHASE,
    SALES,
)
from business_reporting_service.application.ports import Ports
from business_reporting_service.config import Settings
from business_reporting_service.infrastructure.catalog import HTTPCommercialRelationship, HTTPProductCatalog
from business_reporting_service.infrastructure.http_client import AsyncDependencyClient, UserCaller
from business_reporting_service.infrastructure.contract_operational_context import ContractOperationalContext
from business_reporting_service.infrastructure.contract_product_catalog import ContractProductCatalog
from business_reporting_service.infrastructure.inventory import HTTPInventory
from business_reporting_service.infrastructure.operational_context import HTTPOperationalContext
from business_reporting_service.infrastructure.purchase import HTTPPurchase
from business_reporting_service.infrastructure.sales import HTTPSales

PortsFactory = Callable[[str | None], Ports]
"""Recibe la cabecera `Authorization` del usuario y devuelve los puertos de la solicitud."""


@dataclass(frozen=True, slots=True)
class Dependencies:
    ports_factory: PortsFactory
    close: Callable[[], Awaitable[None]]
    # Spec 025 (D27): con `<PROPIETARIO>_READ_SOURCE=contract`, el puerto de OC o de PC de cada solicitud se lee de
    # las vistas de contrato con los permisos del token del usuario (FR-037).
    contract_oc: Callable[[TokenClaims | None], object] | None = None
    contract_pc: Callable[[TokenClaims | None], object] | None = None


def build_http_dependencies(settings: Settings) -> Dependencies:
    timeout = settings.dependency_timeout_seconds
    clients = {
        OPERATIONAL_CONTEXT: AsyncDependencyClient(provider=OPERATIONAL_CONTEXT,
                                                   base_url=settings.operational_context_base_url, timeout_seconds=timeout),
        SALES: AsyncDependencyClient(provider=SALES, base_url=settings.sales_base_url, timeout_seconds=timeout),
        PURCHASE: AsyncDependencyClient(provider=PURCHASE, base_url=settings.purchase_base_url, timeout_seconds=timeout),
        INVENTORY: AsyncDependencyClient(provider=INVENTORY, base_url=settings.inventory_base_url, timeout_seconds=timeout),
        COMMERCIAL_RELATIONSHIP: AsyncDependencyClient(provider=COMMERCIAL_RELATIONSHIP,
                                                       base_url=settings.commercial_relationship_base_url,
                                                       timeout_seconds=timeout),
        PRODUCT_CATALOG: AsyncDependencyClient(provider=PRODUCT_CATALOG, base_url=settings.product_catalog_base_url,
                                               timeout_seconds=timeout),
    }

    def factory(authorization: str | None) -> Ports:
        def user(name: str) -> UserCaller:
            return UserCaller(clients[name], authorization)

        return Ports(
            oc=HTTPOperationalContext(clients[OPERATIONAL_CONTEXT], authorization),
            sales=HTTPSales(user(SALES)),
            purchase=HTTPPurchase(user(PURCHASE)),
            inventory=HTTPInventory(user(INVENTORY)),
            cr=HTTPCommercialRelationship(user(COMMERCIAL_RELATIONSHIP)),
            pc=HTTPProductCatalog(user(PRODUCT_CATALOG)),
        )

    engines = {}
    for name, reads in ((OPERATIONAL_CONTEXT, settings.operational_context_reads),
                        (PRODUCT_CATALOG, settings.product_catalog_reads)):
        if reads is not None and reads.uses_contract:
            engines[name] = create_contract_engine(reads, application_name="business-reporting-service")

    contract_oc = contract_pc = None
    if OPERATIONAL_CONTEXT in engines:
        def contract_oc(claims: TokenClaims | None) -> ContractOperationalContext:
            return ContractOperationalContext(engine=engines[OPERATIONAL_CONTEXT], claims=claims)
    if PRODUCT_CATALOG in engines:
        def contract_pc(claims: TokenClaims | None) -> ContractProductCatalog:
            return ContractProductCatalog(engine=engines[PRODUCT_CATALOG], claims=claims)

    async def close() -> None:
        for client in clients.values():
            await client.aclose()
        for engine in engines.values():
            engine.dispose()

    return Dependencies(factory, close, contract_oc, contract_pc)


def ports_of(request: Request) -> Ports:
    dependencies: Dependencies = request.app.state.dependencies
    ports = dependencies.ports_factory(request.headers.get("authorization"))
    if dependencies.contract_oc is None and dependencies.contract_pc is None:
        return ports
    claims = getattr(request.state, "sio_claims", None)
    if dependencies.contract_oc is not None:
        ports = replace(ports, oc=dependencies.contract_oc(claims))
    if dependencies.contract_pc is not None:
        ports = replace(ports, pc=dependencies.contract_pc(claims))
    return ports
