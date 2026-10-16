"""Rutas de la tasa de impuesto de compra del producto (spec 021, `contracts/commercial-relationship.md` §2).

Permiso propio `perm:commercial-relationship:company_product_purchase_taxes:update` (M-5), distinto del `PUT` del
producto; solo administradores y supervisores. Siempre con membresía en la empresa.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import company_dependency, load_scoped
from commercial_relationship_service.api.dependencies import (
    get_identity,
    get_product_repository,
    get_product_tax_service,
    get_scope_service,
)
from commercial_relationship_service.api.schemas.company_product import CompanyProductResponse
from commercial_relationship_service.api.schemas.company_product_tax import (
    PurchaseTaxBatch,
    PurchaseTaxBatchResponse,
    PurchaseTaxUpdate,
)
from commercial_relationship_service.application.company_product_tax_service import CompanyProductTaxService
from commercial_relationship_service.application.company_scope import (
    SERVICE,
    CompanyScopeService,
    RequestIdentity,
)

RESOURCE = "company_product_purchase_taxes"


def _product(
    company_product_id: UUID,
    identity: RequestIdentity = Depends(get_identity),
    scope: CompanyScopeService = Depends(get_scope_service),
    repository=Depends(get_product_repository),
):
    return load_scoped(repository.get, company_product_id, identity=identity, scope=scope, write=True)


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de la tasa de impuesto de compra."""
    router = APIRouter(tags=["Productos empresariales"])
    permission = auth.permission(SERVICE, RESOURCE, "update")

    @router.put(
        "/company-products/{company_product_id}/purchase-tax",
        response_model=CompanyProductResponse,
        dependencies=[permission],
        summary="Configurar la tasa de impuesto de compra del producto (0 a 100 %; 0 es válido)",
    )
    def set_purchase_tax(
        body: PurchaseTaxUpdate,
        actor: CurrentSubject,
        current=Depends(_product),
        service: CompanyProductTaxService = Depends(get_product_tax_service),
    ):
        model = service.set_one(current, value=body.purchase_tax_percentage, version=body.version, actor=actor)
        return CompanyProductResponse.model_validate(model)

    @router.post(
        "/companies/{company_id}/company-products/purchase-taxes/batch",
        response_model=PurchaseTaxBatchResponse,
        dependencies=[permission],
        summary="Configurar la tasa de impuesto de compra de hasta 100 productos (todo o nada)",
    )
    def set_purchase_taxes(
        body: PurchaseTaxBatch,
        actor: CurrentSubject,
        company_id: UUID = Depends(company_dependency(write=True)),
        service: CompanyProductTaxService = Depends(get_product_tax_service),
    ):
        models = service.set_batch(company_id, [item.model_dump() for item in body.items], actor=actor)
        return PurchaseTaxBatchResponse(items=[CompanyProductResponse.model_validate(model) for model in models])

    return router
