"""Salidas de venta y sus reversos (`contracts/rest-api.md` rutas 2 y 4).

Exigen `perm:inventory:outputs:create` **y** cuenta de servicio (RC-01, R-02).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sio_auth import SIOAuth

from inventory_service.api.identity import SERVICE, ServiceIdentity, require_service_account
from inventory_service.api.openapi import OPERATION_RESPONSES, REVERSAL_RESPONSES, TAG_OUTPUTS
from inventory_service.api.schemas.operations import InventoryOperationResponse, OperationIn, ReversalIn
from inventory_service.api.services import build_operation_service, build_reversal_service, get_repository
from inventory_service.application.operation_service import Caller
from inventory_service.domain.balance_math import OUTPUT
from inventory_service.infrastructure.repository import SqlInventoryRepository


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_OUTPUTS])
    create = [auth.permission(SERVICE, "outputs", "create")]

    @router.post(
        "/inventory-outputs",
        status_code=status.HTTP_201_CREATED,
        response_model=InventoryOperationResponse,
        summary="Aplicar una salida de venta (1 a 100 líneas, todo o nada; nunca saldo negativo)",
        responses=OPERATION_RESPONSES,
        dependencies=create,
    )
    def apply_output(
        body: OperationIn,
        request: Request,
        response: Response,
        identity: Annotated[ServiceIdentity, Depends(require_service_account)],
        repository: Annotated[SqlInventoryRepository, Depends(get_repository)],
    ) -> InventoryOperationResponse:
        result = build_operation_service(request, repository).apply(
            OUTPUT, body, Caller(subject=identity.subject, client_id=identity.client_id)
        )
        if not result.created:
            response.status_code = status.HTTP_200_OK
        return InventoryOperationResponse.from_stored(result.stored)

    @router.post(
        "/inventory-outputs/{operation_id}/reversal",
        status_code=status.HTTP_201_CREATED,
        response_model=InventoryOperationResponse,
        summary="Revertir una salida completa (company_id obligatorio)",
        responses=REVERSAL_RESPONSES,
        dependencies=create,
    )
    def reverse_output(
        operation_id: UUID,
        body: ReversalIn,
        request: Request,
        response: Response,
        identity: Annotated[ServiceIdentity, Depends(require_service_account)],
        repository: Annotated[SqlInventoryRepository, Depends(get_repository)],
    ) -> InventoryOperationResponse:
        result = build_reversal_service(request, repository).reverse(
            OUTPUT, operation_id, body, Caller(subject=identity.subject, client_id=identity.client_id)
        )
        if not result.created:
            response.status_code = status.HTTP_200_OK
        return InventoryOperationResponse.from_stored(result.stored)

    return router
