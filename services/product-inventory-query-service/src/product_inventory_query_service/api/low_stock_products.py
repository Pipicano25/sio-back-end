"""Router de `low-stock-products` (T119; contrato §1 y §4.3). El orden de validación está en `listing_common`."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from sio_auth import SIOAuth
from sio_auth.tokens import TokenClaims

from product_inventory_query_service.api.dependencies import ports_of, runtime_of
from product_inventory_query_service.api.filters.query_params import openapi_parameters, parse_query
from product_inventory_query_service.api.listing_common import BRANCH_ROUTE_NOTE, LISTING_ERRORS, PAGINATION_NOTE, BranchInPath
from product_inventory_query_service.api.openapi import TAG_QUERIES
from product_inventory_query_service.api.presenters import cursor_page, low_stock_pair
from product_inventory_query_service.api.schemas.low_stock import LowStockPair
from product_inventory_query_service.api.schemas.pagination import CursorPage
from product_inventory_query_service.api.security import SERVICE
from product_inventory_query_service.api.visibility import Block, visible_blocks
from product_inventory_query_service.application.exceptions import ForbiddenFilterError
from product_inventory_query_service.application.low_stock_service import low_stock_products
from product_inventory_query_service.domain.query_spec import Endpoint


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_QUERIES])
    permission = auth.permission(SERVICE, "low_stock_products", "read")
    description = (
        "Pares (producto, sucursal) con política activa y existencia estrictamente menor que el mínimo. Exige "
        "además `perm:product-inventory-query:stock:read` y `perm:inventory:product-policies:read`. Permiso: "
        "`perm:product-inventory-query:low_stock_products:read`. Orden predeterminado `shortfall:desc`; un "
        "`sort` explícito por un campo de Commercial Relationship se aplica tal cual. " + PAGINATION_NOTE
    )

    async def run(company_id: UUID, branch_id: UUID | None, request: Request, claims: TokenClaims):
        spec = parse_query(Endpoint.LOW_STOCK_PRODUCTS, company_id, request.query_params.multi_items(),
                           branch_id=branch_id)
        if not {Block.STOCK, Block.MINIMUMS} <= visible_blocks(claims):
            raise ForbiddenFilterError("No tiene permiso para consultar productos bajo el mínimo.")
        result, views = await low_stock_products(spec, ports_of(request), runtime_of(request))
        return cursor_page(result, [low_stock_pair(view) for view in views])

    @router.get(
        "/companies/{company_id}/low-stock-products",
        response_model=CursorPage[LowStockPair],
        response_model_exclude_unset=True,
        summary="Listar pares producto–sucursal bajo el mínimo",
        description=description,
        responses=LISTING_ERRORS,
        openapi_extra={"parameters": openapi_parameters(Endpoint.LOW_STOCK_PRODUCTS)},
    )
    async def get_low_stock_products(company_id: UUID, request: Request, claims: TokenClaims = permission):
        return await run(company_id, None, request, claims)

    @router.get(
        "/companies/{company_id}/branches/{branch_id}/low-stock-products",
        response_model=CursorPage[LowStockPair],
        response_model_exclude_unset=True,
        summary="Listar productos bajo el mínimo de una sucursal",
        description=description + " " + BRANCH_ROUTE_NOTE,
        responses=LISTING_ERRORS,
        openapi_extra={"parameters": openapi_parameters(Endpoint.LOW_STOCK_PRODUCTS, branch_in_path=True)},
    )
    async def get_branch_low_stock_products(company_id: UUID, branch_id: BranchInPath, request: Request,
                                            claims: TokenClaims = permission):
        return await run(company_id, branch_id, request, claims)

    return router
