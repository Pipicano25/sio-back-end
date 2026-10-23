"""Router de `product-overviews` (T107; contrato §1 y §4.1). El orden de validación está en `listing_common`."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from sio_auth import SIOAuth
from sio_auth.tokens import TokenClaims

from product_inventory_query_service.api.dependencies import ports_of, runtime_of
from product_inventory_query_service.api.filters.query_params import openapi_parameters, parse_query
from product_inventory_query_service.api.listing_common import (
    BRANCH_ROUTE_NOTE,
    DEFAULT_SORTS,
    LISTING_ERRORS,
    PAGINATION_NOTE,
    BranchInPath,
    visibility,
)
from product_inventory_query_service.api.openapi import TAG_QUERIES
from product_inventory_query_service.api.presenters import cursor_page, product_overview
from product_inventory_query_service.api.schemas.pagination import CursorPage
from product_inventory_query_service.api.schemas.product_overview import ProductOverview
from product_inventory_query_service.api.security import SERVICE
from product_inventory_query_service.api.visibility import require_filter_blocks, visible_blocks
from product_inventory_query_service.application.product_overview_service import product_overviews
from product_inventory_query_service.domain.query_spec import Endpoint


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_QUERIES])
    permission = auth.permission(SERVICE, "product_overviews", "read")
    description = (
        "Productos de la empresa con su catálogo, presentaciones (cada una con su imagen principal; todas sus "
        "imágenes con `include_images=true`) y, según los permisos, el precio de cada "
        "presentación en una sola lista y las existencias por sucursal. Permiso: "
        "`perm:product-inventory-query:product_overviews:read`. " + DEFAULT_SORTS + " " + PAGINATION_NOTE
    )

    async def run(company_id: UUID, branch_id: UUID | None, request: Request, claims: TokenClaims):
        spec = parse_query(Endpoint.PRODUCT_OVERVIEWS, company_id, request.query_params.multi_items(),
                           branch_id=branch_id)
        blocks = visible_blocks(claims)
        require_filter_blocks(spec.used_filters, blocks)
        seen = visibility(blocks)
        result, views = await product_overviews(spec, seen, ports_of(request), runtime_of(request))
        return cursor_page(result, [
            product_overview(view, with_prices=seen.prices, with_minimums=seen.minimums,
                             include_images=spec.include_images) for view in views
        ])

    @router.get(
        "/companies/{company_id}/product-overviews",
        response_model=CursorPage[ProductOverview],
        response_model_exclude_unset=True,
        summary="Listar productos con presentaciones, imágenes, precios y existencias",
        description=description,
        responses=LISTING_ERRORS,
        openapi_extra={"parameters": openapi_parameters(Endpoint.PRODUCT_OVERVIEWS)},
    )
    async def get_product_overviews(company_id: UUID, request: Request, claims: TokenClaims = permission):
        return await run(company_id, None, request, claims)

    @router.get(
        "/companies/{company_id}/branches/{branch_id}/product-overviews",
        response_model=CursorPage[ProductOverview],
        response_model_exclude_unset=True,
        summary="Listar productos con existencias de una sucursal",
        description=description + " " + BRANCH_ROUTE_NOTE,
        responses=LISTING_ERRORS,
        openapi_extra={"parameters": openapi_parameters(Endpoint.PRODUCT_OVERVIEWS, branch_in_path=True)},
    )
    async def get_branch_product_overviews(company_id: UUID, branch_id: BranchInPath, request: Request,
                                           claims: TokenClaims = permission):
        return await run(company_id, branch_id, request, claims)

    return router
