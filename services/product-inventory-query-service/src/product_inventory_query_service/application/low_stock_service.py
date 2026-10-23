"""Caso de uso de `low-stock-products` (FR-022-50 a FR-022-52; T117).

La unidad es el par (producto, sucursal) con política activa y existencia **estrictamente menor** que el mínimo:
`AT_MINIMUM`, `ABOVE_MINIMUM`, `NO_POLICY` y mínimo 0 nunca aparecen.

- Sin `sort`, conduce Inventory (INV-2 en modo pares, `shortfall:desc`); CR evalúa estado y adopción y PC los
  filtros de catálogo.
- Con `sort` explícito (R-F), conduce CR y el faltante se calcula por lote con `balances/lookup` e INV-1.

El enriquecimiento solo pide PC-1 (unidad base; spec 024: low-stock no trae imágenes): los datos del par ya están en la solicitud.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from product_inventory_query_service.application.enrichment import summaries
from product_inventory_query_service.application.listing import (
    Listing,
    ListingResult,
    PairFacts,
    Ports,
    Runtime,
    run_listing,
)
from product_inventory_query_service.application.ports import CompanyProduct, ProductSummary
from product_inventory_query_service.domain.pagination import Page
from product_inventory_query_service.domain.query_spec import QuerySpec


@dataclass(frozen=True, slots=True)
class PairView:
    product: CompanyProduct
    pair: PairFacts
    summary: ProductSummary | None


async def low_stock_products(spec: QuerySpec, ports: Ports, runtime: Runtime) -> tuple[ListingResult, list[PairView]]:
    async def enrich(listing: Listing, page: Page) -> list[PairView]:
        keys: list[tuple[UUID, UUID]] = [item.key for item in page.items]
        products = [listing.gateway.facts.products[product_id] for product_id, _ in keys]
        catalog = await summaries(listing.gateway, [p.global_product_id for p in products])
        return [
            PairView(product, listing.gateway.facts.pairs[key], catalog.get(product.global_product_id))
            for key, product in zip(keys, products, strict=True)
        ]

    return await run_listing(spec, ports, runtime, enrich=enrich)
