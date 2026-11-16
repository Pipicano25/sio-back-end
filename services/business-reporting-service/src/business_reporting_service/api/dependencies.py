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
    # Spec 025 (D27): con OPERATIONAL_CONTEXT_READ_SOURCE=contract, envuelve el puerto de OC de cada solicitud.
    contract_oc: Callable[[TokenClaims | None, object], object] | None = None


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

    oc_reads = settings.operational_context_reads
    oc_engine = (
        create_contract_engine(oc_reads, application_name="business-reporting-service")
        if oc_reads is not None and oc_reads.uses_contract
        else None
    )
    contract_oc = None
    if oc_engine is not None:
        def contract_oc(claims: TokenClaims | None, http: HTTPOperationalContext) -> ContractOperationalContext:
            return ContractOperationalContext(engine=oc_engine, claims=claims, http=http)

    async def close() -> None:
        for client in clients.values():
            await client.aclose()
        if oc_engine is not None:
            oc_engine.dispose()

    return Dependencies(factory, close, contract_oc)


def ports_of(request: Request) -> Ports:
    dependencies: Dependencies = request.app.state.dependencies
    ports = dependencies.ports_factory(request.headers.get("authorization"))
    if dependencies.contract_oc is None:
        return ports
    claims = getattr(request.state, "sio_claims", None)
    return replace(ports, oc=dependencies.contract_oc(claims, ports.oc))
