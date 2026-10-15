"""Confirmación, recepción, anulación y operaciones (`contracts/rest-api.md` rutas 9–12; spec 020).

El usuario humano se resuelve antes que las cabeceras: un token técnico recibe `403`
antes de cualquier validación (RC-05).

Confirmar, recibir y anular exigen `Idempotency-Key`; la misma clave repetida devuelve el
resultado de la primera solicitud (o la reanuda si quedó `PENDING`), nunca una segunda
entrada ni un segundo reverso en Inventory (RC-01, RC-MVP-2).

Spec 020: confirmar **no** mueve inventario; la recepción física completa aplica la entrada.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from sio_auth import SIOAuth

from purchase_service.api.dependencies import ActorDep, CompanyReader, CorrelationId, IdempotencyKey, ServicesDep
from purchase_service.api.identity import SERVICE
from purchase_service.api.openapi import OPERATION_RESPONSES, READ_RESPONSES, TAG_OPERATIONS
from purchase_service.api.schemas.purchases import CancelIn, OperationResponse, PurchaseResponse, ReceiptIn, VersionIn


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_OPERATIONS])

    @router.post(
        "/companies/{company_id}/purchases/{purchase_id}/confirmation",
        response_model=PurchaseResponse,
        summary="Confirmar la compra (queda pendiente de recepción; no mueve inventario)",
        responses=OPERATION_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchases", "update")],
    )
    def confirm_purchase(
        company_id: UUID,
        purchase_id: UUID,
        body: VersionIn,
        actor: ActorDep,
        key: IdempotencyKey,
        correlation: CorrelationId,
        services: ServicesDep,
    ) -> PurchaseResponse:
        view = services.confirmations().confirm(company_id, purchase_id, body.version, key, correlation, actor)
        return PurchaseResponse.of(view)

    @router.post(
        "/companies/{company_id}/purchases/{purchase_id}/receipt",
        response_model=PurchaseResponse,
        summary="Confirmar la recepción física completa e ingresar la mercancía en Inventory",
        responses=OPERATION_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchases", "update")],
    )
    def receive_purchase(
        company_id: UUID,
        purchase_id: UUID,
        body: ReceiptIn,
        actor: ActorDep,
        key: IdempotencyKey,
        correlation: CorrelationId,
        services: ServicesDep,
    ) -> PurchaseResponse:
        view = services.receipts().receive(
            company_id, purchase_id, body.version, body.full_receipt_confirmed, key, correlation, actor
        )
        return PurchaseResponse.of(view)

    @router.post(
        "/companies/{company_id}/purchases/{purchase_id}/cancellation",
        response_model=PurchaseResponse,
        summary="Anular la compra (revierte la entrada en Inventory si estaba recibida)",
        responses=OPERATION_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchases", "delete")],
    )
    def cancel_purchase(
        company_id: UUID,
        purchase_id: UUID,
        body: CancelIn,
        actor: ActorDep,
        key: IdempotencyKey,
        correlation: CorrelationId,
        services: ServicesDep,
    ) -> PurchaseResponse:
        view = services.cancellations().cancel(
            company_id, purchase_id, body.version, body.reason, key, correlation, actor
        )
        return PurchaseResponse.of(view)

    @router.get(
        "/companies/{company_id}/purchases/{purchase_id}/operations",
        response_model=list[OperationResponse],
        summary="Operaciones de confirmación, recepción y anulación de una compra",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_operations", "read")],
    )
    def list_operations(company_id: CompanyReader, purchase_id: UUID, services: ServicesDep) -> list[OperationResponse]:
        return [OperationResponse.of(operation) for operation in services.queries().operations(company_id, purchase_id)]

    @router.get(
        "/companies/{company_id}/purchase-operations/{operation_id}",
        response_model=OperationResponse,
        summary="Operación por id",
        responses=READ_RESPONSES,
        dependencies=[auth.permission(SERVICE, "purchase_operations", "read")],
    )
    def get_operation(company_id: CompanyReader, operation_id: UUID, services: ServicesDep) -> OperationResponse:
        return OperationResponse.of(services.queries().operation(company_id, operation_id))

    return router
