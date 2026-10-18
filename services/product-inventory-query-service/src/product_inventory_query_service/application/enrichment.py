"""Enriquecimiento de la página final (FR-022-137; research R-11).

Solo para los productos de la página (a lo sumo 20) y solo con los bloques visibles (FR-022-14), en una tanda
paralela:

| Llamada | Cuándo |
|---|---|
| PC-1 (resumen de catálogo e imagen) | Siempre |
| CR-2 (presentaciones de la empresa) | Siempre |
| `presentations/batch-lookup` de PC (código, nombre y factor) | Después de CR-2, en paralelo con los precios |
| Precios (`applicable-prices/resolve`) | Después de CR-2, solo en `product-overviews` con el bloque de precios |
| `balances/lookup` por sucursal | Con el bloque de existencias; solo los ids que la búsqueda no trajo ya |
| INV-1 por sucursal | Con existencias **y** mínimos; solo los ids que faltan |

PC-3 no se usa: PC-1 ya entrega la unidad base con su código y nombre. Nada se inventa: un producto global que
PC no encuentra queda sin datos de catálogo (`canonical_name = null`, `has_image = false`) y se registra; una
presentación sin factor no tiene equivalencia.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from uuid import UUID

from product_inventory_query_service.application.exceptions import (
    COMMERCIAL_RELATIONSHIP,
    DependencyUnavailableError,
)
from product_inventory_query_service.application.listing import Gateway
from product_inventory_query_service.application.ports import (
    Balance,
    CompanyPresentation,
    CompanyProduct,
    Policy,
    PresentationInfo,
    PriceLine,
    PriceResult,
    ProductSummary,
)
from product_inventory_query_service.domain.stock import (
    BranchStock,
    Equivalence,
    branch_stock,
    equivalence,
    total_quantity,
)
from product_inventory_query_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)


@dataclass(frozen=True, slots=True)
class PresentationView:
    company: CompanyPresentation
    info: PresentationInfo | None
    price: PriceResult | None


@dataclass(frozen=True, slots=True)
class StockView:
    branches: list[BranchStock]
    equivalences: list[Equivalence]

    @property
    def total(self):
        return total_quantity(self.branches)


@dataclass(frozen=True, slots=True)
class ProductView:
    product: CompanyProduct
    summary: ProductSummary | None
    presentations: list[PresentationView]
    stock: StockView | None


async def summaries(gateway: Gateway, global_ids: list[UUID]) -> dict[UUID, ProductSummary]:
    ids = list(dict.fromkeys(global_ids))
    if not ids:
        return {}
    found = await gateway.registry.once("summaries", ids, lambda: gateway.ports.pc.summaries(ids))
    if set(ids) - set(found):
        logger.error("Incidente de integridad: Product Catalog no encontró %d productos globales adoptados",
                     len(set(ids) - set(found)))
    return found


async def stock_data(gateway: Gateway, branch_ids: list[UUID], ids: list[UUID], *, with_minimums: bool
                     ) -> tuple[list[dict[UUID, Balance]], list[dict[UUID, Policy | None]]]:
    balances = asyncio.gather(*(gateway.balances(b, ids) for b in branch_ids))
    if not with_minimums:
        return await balances, []
    return tuple(await asyncio.gather(balances, asyncio.gather(*(gateway.policies(b, ids) for b in branch_ids))))


async def enrich_products(gateway: Gateway, products: list[CompanyProduct], branch_ids: list[UUID], *,
                          with_prices: bool, price_list_id: UUID | None, with_stock: bool,
                          with_minimums: bool) -> list[ProductView]:
    if not products:
        return []
    company_ids = [p.id for p in products]

    async def presentations() -> tuple[list[CompanyPresentation], dict[UUID, PresentationInfo], dict[UUID, PriceResult]]:
        rows = await gateway.registry.once(
            "presentations_by_products", company_ids,
            lambda: gateway.ports.cr.presentations_by_products(gateway.company_id, company_ids),
        )
        global_ids = list(dict.fromkeys(r.global_product_presentation_id for r in rows))
        lines = [PriceLine(r.company_product_id, r.id, price_list_id) for r in rows]

        async def infos():
            if not global_ids:
                return {}
            return await gateway.registry.once("presentations", global_ids,
                                               lambda: gateway.ports.pc.presentations(global_ids))

        async def prices():
            if not with_prices or not lines:
                return {}
            results = await gateway.registry.once(
                "resolve_prices", (price_list_id, [line.company_product_presentation_id for line in lines]),
                lambda: gateway.ports.cr.resolve_prices(gateway.company_id, lines),
            )
            return {price.company_product_presentation_id: price for price in results}

        found_infos, found_prices = await asyncio.gather(infos(), prices())
        return rows, found_infos, found_prices

    async def stock():
        if not with_stock:
            return [], []
        return await stock_data(gateway, branch_ids, company_ids, with_minimums=with_minimums)

    catalog, (rows, infos, prices), (balances, policies) = await asyncio.gather(
        summaries(gateway, [p.global_product_id for p in products]), presentations(), stock()
    )
    if with_prices:
        for row in rows:
            if row.id not in prices:
                # Una línea sin respuesta no se convierte en "sin precio": es una respuesta inválida (`503`).
                raise DependencyUnavailableError(COMMERCIAL_RELATIONSHIP, "applicable_prices", "linea_sin_respuesta")

    by_product: dict[UUID, list[CompanyPresentation]] = {}
    for row in rows:
        by_product.setdefault(row.company_product_id, []).append(row)

    views = []
    for product in products:
        presentation_views = [
            PresentationView(row, infos.get(row.global_product_presentation_id), prices.get(row.id))
            for row in by_product.get(product.id, [])
        ]
        stock_view = None
        if with_stock:
            branches = [
                branch_stock(branch_id, balances[index][product.id],
                             policies[index][product.id] if with_minimums else None, with_minimums=with_minimums)
                for index, branch_id in enumerate(branch_ids)
            ]
            total = total_quantity(branches)
            equivalences = [
                equivalence(view.company.id, total, view.info.base_quantity)
                for view in presentation_views
                if view.info is not None and view.info.base_quantity is not None and view.info.base_quantity > 0
            ]
            stock_view = StockView(branches, equivalences)
        views.append(ProductView(product, catalog.get(product.global_product_id), presentation_views, stock_view))
    return views
