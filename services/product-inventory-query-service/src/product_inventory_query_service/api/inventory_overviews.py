"""Router de `inventory-overviews` (T111; contrato §1 y §4.2). El orden de validación está en `listing_common`."""

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
from product_inventory_query_service.api.presenters import cursor_page, inventory_overview
from product_inventory_query_service.api.schemas.inventory_overview import InventoryOverview
from product_inventory_query_service.api.schemas.pagination import CursorPage
from product_inventory_query_service.api.security import SERVICE
from product_inventory_query_service.api.visibility import require_filter_blocks, visible_blocks
from product_inventory_query_service.application.inventory_overview_service import inventory_overviews
from product_inventory_query_service.domain.query_spec import Endpoint


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_QUERIES])
    permission = auth.permission(SERVICE, "inventory_overviews", "read")
    description = (
        "Productos con control de inventario y sus existencias en la unidad base, por sucursal y consolidadas, "
        "con equivalencias por presentación (cada una con su imagen principal; todas sus imágenes con "
        "`include_images=true`) y, con el permiso de mínimos, el estado frente al mínimo. Cualquier "
        "sucursal de la empresa se puede leer con membresía `ACTIVE`. Permiso: "
        "`perm:product-inventory-query:inventory_overviews:read`. " + DEFAULT_SORTS + " " + PAGINATION_NOTE
    )

    async def run(company_id: UUID, branch_id: UUID | None, request: Request, claims: TokenClaims):
        spec = parse_query(Endpoint.INVENTORY_OVERVIEWS, company_id, request.query_params.multi_items(),
                           branch_id=branch_id)
        blocks = visible_blocks(claims)
        require_filter_blocks(spec.used_filters, blocks)
        seen = visibility(blocks)
        result, views = await inventory_overviews(spec, seen, ports_of(request), runtime_of(request))
        return cursor_page(result, [inventory_overview(view, with_minimums=seen.minimums,
                                                       include_images=spec.include_images) for view in views])

    @router.get(
        "/companies/{company_id}/inventory-overviews",
        response_model=CursorPage[InventoryOverview],
        response_model_exclude_unset=True,
        summary="Listar existencias por producto, sucursal y empresa",
        description=description,
        responses=LISTING_ERRORS,
        openapi_extra={"parameters": openapi_parameters(Endpoint.INVENTORY_OVERVIEWS)},
    )
    async def get_inventory_overviews(company_id: UUID, request: Request, claims: TokenClaims = permission):
        return await run(company_id, None, request, claims)

    @router.get(
        "/companies/{company_id}/branches/{branch_id}/inventory-overviews",
        response_model=CursorPage[InventoryOverview],
        response_model_exclude_unset=True,
        summary="Listar existencias por producto de una sucursal",
        description=description + " " + BRANCH_ROUTE_NOTE,
        responses=LISTING_ERRORS,
        openapi_extra={"parameters": openapi_parameters(Endpoint.INVENTORY_OVERVIEWS, branch_in_path=True)},
    )
    async def get_branch_inventory_overviews(company_id: UUID, branch_id: BranchInPath, request: Request,
                                             claims: TokenClaims = permission):
        return await run(company_id, branch_id, request, claims)

    return router
