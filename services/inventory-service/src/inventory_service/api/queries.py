"""Consultas de stock, kardex y operaciones (`contracts/rest-api.md` rutas 5 a 10).

Permisos: `balances:read` (rutas 5–7) y `movements:read` (rutas 8–10), más el alcance
por empresa de `api/scope.py` (membresía o `platform:lookup`).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sio_auth import SIOAuth

from inventory_service.api.identity import SERVICE
from inventory_service.api.openapi import QUERY_RESPONSES, TAG_QUERIES
from inventory_service.api.schemas.operations import InventoryOperationResponse
from inventory_service.api.schemas.queries import (
    BalanceLookupIn,
    BalanceLookupResponse,
    BalancePage,
    BalanceResponse,
    BalancesQuery,
    KardexMovement,
    KardexPage,
    KardexQuery,
    total_pages,
)
from inventory_service.api.scope import company_scope
from inventory_service.api.services import get_repository
from inventory_service.application.query_service import QueryService
from inventory_service.infrastructure.repository import SqlInventoryRepository

Company = Annotated[UUID, Depends(company_scope)]


def get_query_service(repository: Annotated[SqlInventoryRepository, Depends(get_repository)]) -> QueryService:
    return QueryService(repository)


Service = Annotated[QueryService, Depends(get_query_service)]


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_QUERIES], responses=QUERY_RESPONSES)
    balances_read = [auth.permission(SERVICE, "balances", "read")]
    movements_read = [auth.permission(SERVICE, "movements", "read")]
    branch_base = "/companies/{company_id}/branches/{branch_id}"

    @router.get(f"{branch_base}/balances", response_model=BalancePage, summary="Stock de una sucursal", dependencies=balances_read)
    def list_balances(
        company_id: Company, branch_id: UUID, query: Annotated[BalancesQuery, Query()], service: Service
    ) -> BalancePage:
        result = service.stock(
            company_id,
            branch_id,
            product_id=query.company_product_id,
            in_stock_only=query.in_stock_only,
            page=query.page,
            page_size=query.page_size,
        )
        return BalancePage(
            items=[BalanceResponse.of(company_id, branch_id, row.company_product_id, row) for row in result.items],
            page=query.page,
            page_size=query.page_size,
            total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )

    @router.get(
        f"{branch_base}/balances/{{company_product_id}}",
        response_model=BalanceResponse,
        summary="Saldo de un producto en una sucursal (0 si no tiene movimientos)",
        dependencies=balances_read,
    )
    def get_balance(company_id: Company, branch_id: UUID, company_product_id: UUID, service: Service) -> BalanceResponse:
        row = service.balance(company_id, branch_id, company_product_id)
        return BalanceResponse.of(company_id, branch_id, company_product_id, row)

    @router.post(
        f"{branch_base}/balances/lookup",
        response_model=BalanceLookupResponse,
        summary="Saldos de 1 a 100 productos en una sucursal",
        dependencies=balances_read,
    )
    def lookup_balances(company_id: Company, branch_id: UUID, body: BalanceLookupIn, service: Service) -> BalanceLookupResponse:
        products = list(dict.fromkeys(body.company_product_ids))
        rows = service.balances(company_id, branch_id, products)
        return BalanceLookupResponse(
            items=[BalanceResponse.of(company_id, branch_id, product, rows.get(product)) for product in products]
        )

    @router.get(
        f"{branch_base}/kardex/{{company_product_id}}",
        response_model=KardexPage,
        summary="Kardex de un producto en una sucursal (orden cronológico)",
        dependencies=movements_read,
    )
    def get_kardex(
        company_id: Company,
        branch_id: UUID,
        company_product_id: UUID,
        query: Annotated[KardexQuery, Query()],
        service: Service,
    ) -> KardexPage:
        result = service.kardex(
            company_id,
            branch_id,
            company_product_id,
            occurred_at_from=query.occurred_at_from,
            occurred_at_to=query.occurred_at_to,
            movement_type=query.movement_type,
            origin_type=query.origin_type,
            origin_id=query.origin_id,
            page=query.page,
            page_size=query.page_size,
        )
        return KardexPage(
            items=[KardexMovement.of(row) for row in result.items],
            page=query.page,
            page_size=query.page_size,
            total_records=result.total_records,
            total_pages=total_pages(result.total_records, query.page_size),
        )

    @router.get(
        "/companies/{company_id}/inventory-operations/{operation_id}",
        response_model=InventoryOperationResponse,
        response_model_exclude_unset=True,
        summary="Operación por id con sus movimientos",
        dependencies=movements_read,
    )
    def get_operation(company_id: Company, operation_id: UUID, service: Service) -> InventoryOperationResponse:
        return InventoryOperationResponse.from_stored(service.operation(company_id, operation_id), with_balances=False)

    @router.get(
        "/companies/{company_id}/inventory-operations/by-key/{operation_key}",
        response_model=InventoryOperationResponse,
        response_model_exclude_unset=True,
        summary="Operación por su clave de operación",
        dependencies=movements_read,
    )
    def get_operation_by_key(company_id: Company, operation_key: UUID, service: Service) -> InventoryOperationResponse:
        return InventoryOperationResponse.from_stored(service.operation_by_key(company_id, operation_key), with_balances=False)

    return router
