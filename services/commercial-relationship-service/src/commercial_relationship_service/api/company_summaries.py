"""Resumen de las empresas del usuario (`contracts/rest-api.md` §4; FR-046, DS-18)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sio_auth import CurrentClaims, SioPermission, SIOAuth

from commercial_relationship_service.api.dependencies import (
    get_customer_repository,
    get_product_repository,
    get_supplier_repository,
)
from commercial_relationship_service.api.schemas.common import PaginatedResponse
from commercial_relationship_service.api.schemas.company_summary import CompanySummaryResponse
from commercial_relationship_service.application.company_scope import SERVICE, grants_allow
from commercial_relationship_service.application.company_summary_service import (
    CompanySummaryService,
)

CUSTOMERS_READ = SioPermission(SERVICE, "company_customers", "read")
SUPPLIERS_READ = SioPermission(SERVICE, "company_suppliers", "read")


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router del resumen de empresas."""
    router = APIRouter(tags=["Resumen de empresas"])

    @router.get(
        "/company-summaries",
        response_model=PaginatedResponse[CompanySummaryResponse],
        dependencies=[auth.permission(SERVICE, "company_products", "read")],
        summary="Resumen de mis empresas: razón social y conteos por estado",
    )
    def list_company_summaries(
        request: Request,
        claims: CurrentClaims,
        page: int = Query(default=1, ge=1, description="Número de página solicitado."),
        page_size: int = Query(
            default=1, ge=1, le=100, description="Empresas por página (por defecto una)."
        ),
        products=Depends(get_product_repository),
        customers=Depends(get_customer_repository),
        suppliers=Depends(get_supplier_repository),
    ):
        state = request.app.state
        service = CompanySummaryService(
            state.access_directory_factory(request),
            lambda: state.company_directory_factory(request),
            lambda: state.party_directory_factory(request),
            products=products,
            customers=customers if grants_allow(claims.permissions, CUSTOMERS_READ) else None,
            suppliers=suppliers if grants_allow(claims.permissions, SUPPLIERS_READ) else None,
        )
        result = service.summarize(page=page, page_size=page_size)
        return PaginatedResponse[CompanySummaryResponse](
            items=[CompanySummaryResponse.model_validate(item) for item in result.items],
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    return router
