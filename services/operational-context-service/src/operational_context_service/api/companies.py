"""Router HTTP de empresas (`contracts/rest-api.md`, sección 1).

Los errores de aplicación los traduce `api/errors.py`; este módulo no asigna
estados HTTP de error.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from operational_context_service.api.dependencies import get_company_service
from operational_context_service.api.filters.company_filters import company_filters
from operational_context_service.api.pagination import PaginationParams
from operational_context_service.api.schemas.common import PaginatedResponse, StatusActionRequest
from operational_context_service.api.schemas.company import (
    CompanyCreate,
    CompanyResponse,
    CompanyUpdate,
)
from operational_context_service.application.company_service import CompanyService
from operational_context_service.application.ports import CompanyFilters

SERVICE = "operational-context"
RESOURCE = "companies"
BASE_PATH = "/companies"


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de empresas."""
    router = APIRouter(prefix=BASE_PATH, tags=["Empresas"])

    @router.get(
        "",
        response_model=PaginatedResponse[CompanyResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar empresas",
    )
    def list_companies(
        pagination: PaginationParams = Depends(),
        filters: CompanyFilters = Depends(company_filters),
        service: CompanyService = Depends(get_company_service),
    ) -> PaginatedResponse[CompanyResponse]:
        """Página de empresas; por defecto solo `ACTIVE` (FR-015)."""
        result = service.list(filters, page=pagination.page, page_size=pagination.page_size)

        return PaginatedResponse[CompanyResponse](
            items=[CompanyResponse.model_validate(item) for item in result.items],
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.get(
        "/{company_id}",
        response_model=CompanyResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar una empresa (contrato Provider)",
    )
    def get_company(
        company_id: UUID,
        service: CompanyService = Depends(get_company_service),
    ):
        """Empresa por UUID en cualquier estado (FR-050)."""
        return service.get(company_id)

    @router.post(
        "",
        response_model=CompanyResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Registrar una empresa",
    )
    def create_company(
        payload: CompanyCreate,
        actor_id: CurrentSubject,
        response: Response,
        service: CompanyService = Depends(get_company_service),
    ):
        """Registra una empresa vinculada a su organización (FR-010 a FR-014)."""
        company = service.create(payload.model_dump(), actor_id=actor_id)
        response.headers["Location"] = f"/api/v1{BASE_PATH}/{company.id}"

        return company

    @router.put(
        "/{company_id}",
        response_model=CompanyResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Modificar una empresa",
    )
    def update_company(
        company_id: UUID,
        payload: CompanyUpdate,
        actor_id: CurrentSubject,
        service: CompanyService = Depends(get_company_service),
    ):
        """Reemplazo completo con versión esperada; sin cambios no escribe (FR-063)."""
        data = payload.model_dump()
        expected_version = data.pop("version")

        return service.update(
            company_id,
            data,
            expected_version=expected_version,
            actor_id=actor_id,
        )

    @router.post(
        "/{company_id}/deactivate",
        response_model=CompanyResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "delete")],
        summary="Inactivar una empresa (no elimina)",
    )
    def deactivate_company(
        company_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        service: CompanyService = Depends(get_company_service),
    ):
        """Inactiva sin eliminar ni modificar sus sucursales (D7, DS-07)."""
        return service.deactivate(company_id, expected_version=payload.version, actor_id=actor_id)

    @router.post(
        "/{company_id}/reactivate",
        response_model=CompanyResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Reactivar una empresa",
    )
    def reactivate_company(
        company_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        service: CompanyService = Depends(get_company_service),
    ):
        """Reactiva una empresa inactiva (DS-11)."""
        return service.reactivate(company_id, expected_version=payload.version, actor_id=actor_id)

    return router
