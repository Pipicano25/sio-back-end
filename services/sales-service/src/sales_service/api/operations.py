"""Confirmación, anulación y operaciones (`contracts/rest-api.md` rutas 10–13).

El usuario humano se resuelve antes que las cabeceras: un token técnico recibe `403`
antes de cualquier validación (RC-05).

Confirmar y anular exigen `Idempotency-Key`; la misma clave repetida devuelve el
resultado de la primera solicitud (o la reanuda si quedó `PENDING`), nunca una segunda
salida ni un segundo reverso en Inventory (RC-01).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request, Response
from sio_auth import SIOAuth

from sales_service.api.dependencies import ActorDep, CompanyReader, CorrelationId, IdempotencyKey, ServicesDep
from sales_service.api.identity import SERVICE
from sales_service.api.openapi import OPERATION_RESPONSES, READ_RESPONSES, TAG_OPERATIONS
from sales_service.api.profitability import present
from sales_service.api.schemas.sales import CancelIn, OperationResponse, SaleResponse, VersionIn


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_OPERATIONS])

    @router.post(
        "/companies/{company_id}/sales/{sale_id}/confirmation",
        response_model=SaleResponse,
        summary="Confirmar la venta y descontar el inventario",
        responses=OPERATION_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sales", "update")],
    )
    def confirm_sale(
        company_id: UUID,
        sale_id: UUID,
        body: VersionIn,
        request: Request,
        actor: ActorDep,
        key: IdempotencyKey,
        correlation: CorrelationId,
        services: ServicesDep,
    ) -> Response:
        view = services.confirmations().confirm(company_id, sale_id, body.version, key, correlation, actor)
        return present(request, SaleResponse.of(view))

    @router.post(
        "/companies/{company_id}/sales/{sale_id}/cancellation",
        response_model=SaleResponse,
        summary="Anular la venta (revierte la salida en Inventory si estaba confirmada)",
        responses=OPERATION_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sales", "delete")],
    )
    def cancel_sale(
        company_id: UUID,
        sale_id: UUID,
        body: CancelIn,
        request: Request,
        actor: ActorDep,
        key: IdempotencyKey,
        correlation: CorrelationId,
        services: ServicesDep,
    ) -> Response:
        view = services.cancellations().cancel(
            company_id, sale_id, body.version, body.reason, key, correlation, actor
        )
        return present(request, SaleResponse.of(view))

    @router.get(
        "/companies/{company_id}/sales/{sale_id}/operations",
        response_model=list[OperationResponse],
        summary="Operaciones de confirmación y anulación de una venta",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sale_operations", "read")],
    )
    def list_operations(company_id: CompanyReader, sale_id: UUID, services: ServicesDep) -> list[OperationResponse]:
        return [OperationResponse.of(operation) for operation in services.queries().operations(company_id, sale_id)]

    @router.get(
        "/companies/{company_id}/sale-operations/{operation_id}",
        response_model=OperationResponse,
        summary="Operación por id",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "sale_operations", "read")],
    )
    def get_operation(company_id: CompanyReader, operation_id: UUID, services: ServicesDep) -> OperationResponse:
        return OperationResponse.of(services.queries().operation(company_id, operation_id))

    return router
