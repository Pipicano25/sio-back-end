"""Rutas de condiciones de pago del proveedor (`contracts/rest-api.md` §3 de la 010, contrato Provider)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import company_dependency, load_scoped
from commercial_relationship_service.api.dependencies import (
    get_identity,
    get_payment_condition_repository,
    get_payment_condition_service,
    get_scope_service,
)
from commercial_relationship_service.api.filters.supplier_payment_condition_filters import (
    SupplierPaymentConditionFilters,
)
from commercial_relationship_service.api.pagination import PaginationParams
from commercial_relationship_service.api.schemas.common import PaginatedResponse, VersionRequest
from commercial_relationship_service.api.schemas.supplier_payment_condition import (
    SupplierPaymentConditionCreate,
    SupplierPaymentConditionResponse,
    SupplierPaymentConditionUpdate,
)
from commercial_relationship_service.application.company_scope import (
    SERVICE,
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.supplier_payment_condition_service import (
    SupplierPaymentConditionService,
)

RESOURCE = "supplier_payment_conditions"
BASE = "/supplier-payment-conditions"


def _resource(*, write: bool, allow_inactive_company: bool = False, lookup: bool = False):
    def dependency(
        condition_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        repository=Depends(get_payment_condition_repository),
    ):
        return load_scoped(
            repository.get,
            condition_id,
            identity=identity,
            scope=scope,
            write=write,
            allow_inactive_company=allow_inactive_company,
            lookup=lookup,
        )

    return dependency


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de condiciones de pago del proveedor."""
    router = APIRouter(tags=["Condiciones de pago del proveedor"])

    def permission(action: str):
        return auth.permission(SERVICE, RESOURCE, action)

    @router.get(
        "/companies/{company_id}" + BASE,
        response_model=PaginatedResponse[SupplierPaymentConditionResponse],
        dependencies=[permission("read")],
        summary="Listar las condiciones de pago de los proveedores de una empresa",
    )
    def list_conditions(
        company_id: UUID = Depends(company_dependency(write=False)),
        pagination: PaginationParams = Depends(),
        filters: SupplierPaymentConditionFilters = Depends(),
        repository=Depends(get_payment_condition_repository),
    ):
        page = repository.list_page(
            company_id,
            status=filters.status,
            search=None,
            filters=filters.columns,
            page=pagination.page,
            page_size=pagination.page_size,
            conditions=() if filters.applicable_at is None else repository.applicable_at(filters.applicable_at),
        )
        return PaginatedResponse[SupplierPaymentConditionResponse](
            items=[SupplierPaymentConditionResponse.model_validate(item) for item in page.items],
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.post(
        "/companies/{company_id}" + BASE,
        response_model=SupplierPaymentConditionResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission("create")],
        summary="Registrar una condición de pago de un proveedor",
    )
    def create_condition(
        body: SupplierPaymentConditionCreate,
        response: Response,
        actor: CurrentSubject,
        company_id: UUID = Depends(company_dependency(write=True)),
        service: SupplierPaymentConditionService = Depends(get_payment_condition_service),
    ):
        model = service.create(company_id, body.model_dump(), actor=actor)
        response.headers["Location"] = f"/api/v1{BASE}/{model.id}"
        return SupplierPaymentConditionResponse.model_validate(model)

    @router.get(
        BASE + "/{condition_id}",
        response_model=SupplierPaymentConditionResponse,
        dependencies=[permission("read")],
        summary="Consultar una condición de pago por UUID (Provider)",
    )
    def get_condition(current=Depends(_resource(write=False, lookup=True))):
        return SupplierPaymentConditionResponse.model_validate(current)

    @router.put(
        BASE + "/{condition_id}",
        response_model=SupplierPaymentConditionResponse,
        dependencies=[permission("update")],
        summary="Modificar una condición de pago (en cualquier estado)",
    )
    def update_condition(
        body: SupplierPaymentConditionUpdate,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: SupplierPaymentConditionService = Depends(get_payment_condition_service),
    ):
        values = body.model_dump(exclude={"version"})
        model = service.update(current, values, version=body.version, actor=actor)
        return SupplierPaymentConditionResponse.model_validate(model)

    @router.post(
        BASE + "/{condition_id}/deactivate",
        response_model=SupplierPaymentConditionResponse,
        dependencies=[permission("delete")],
        summary="Inactivar una condición de pago",
    )
    def deactivate_condition(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True, allow_inactive_company=True)),
        service: SupplierPaymentConditionService = Depends(get_payment_condition_service),
    ):
        model = service.deactivate(current, version=body.version, actor=actor)
        return SupplierPaymentConditionResponse.model_validate(model)

    @router.post(
        BASE + "/{condition_id}/reactivate",
        response_model=SupplierPaymentConditionResponse,
        dependencies=[permission("update")],
        summary="Reactivar una condición de pago",
    )
    def reactivate_condition(
        body: VersionRequest,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: SupplierPaymentConditionService = Depends(get_payment_condition_service),
    ):
        model = service.reactivate(current, version=body.version, actor=actor)
        return SupplierPaymentConditionResponse.model_validate(model)

    return router
