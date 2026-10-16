"""Rutas de las actualizaciones automáticas de precio (spec 021, `contracts/commercial-relationship.md` §3–§4).

- **A1** `POST /companies/{company_id}/automatic-price-update-requests`: entrega técnica desde Purchase (EXC-001).
  Exige `perm:commercial-relationship:automatic_price_update_requests:submit` **y** una identidad técnica; es la única
  escritura técnica sin membresía en la empresa (DS-05). Un usuario humano recibe `403` aunque tenga el permiso.
- **A2** `GET /companies/{company_id}/automatic-price-applications`, **A3** `GET …/{application_id}` y **A4**
  `POST …/{application_id}/resolution`: consulta y resolución administrativa con
  `perm:commercial-relationship:automatic_price_applications:{read,resolve}` y membresía en la empresa. Solo los
  tienen administradores y supervisores, porque exponen costos y porcentajes (FR-021-32a).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sio_auth import FORBIDDEN_DETAIL, CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import company_dependency
from commercial_relationship_service.api.dependencies import (
    get_automatic_price_application_repository,
    get_automatic_price_request_service,
    get_automatic_price_resolution_service,
    get_identity,
)
from commercial_relationship_service.api.openapi import TAG_PRICING_POLICIES
from commercial_relationship_service.api.pagination import PaginationParams
from commercial_relationship_service.api.schemas.automatic_price import (
    ApplicationResolution,
    ApplicationSummary,
    AutomaticPriceApplicationResponse,
    PriceUpdateRequestAccepted,
    PriceUpdateRequestIn,
)
from commercial_relationship_service.api.schemas.common import PaginatedResponse
from commercial_relationship_service.application.automatic_price_application_service import (
    AutomaticPriceResolutionService,
)
from commercial_relationship_service.application.automatic_price_request_service import AutomaticPriceRequestService
from commercial_relationship_service.application.company_scope import SERVICE, RequestIdentity
from commercial_relationship_service.application.exceptions import NotFoundError
from commercial_relationship_service.domain.currency import currency_places
from commercial_relationship_service.infrastructure.models import AUTOMATIC_STATUSES

APPLICATIONS = "/companies/{company_id}/automatic-price-applications"
STATUS_PATTERN = "^(" + "|".join(AUTOMATIC_STATUSES) + ")$"

logger = logging.getLogger("sio_auth")


def require_technical_identity(request: Request, identity: RequestIdentity = Depends(get_identity)) -> RequestIdentity:
    """DS-05: solo cuentas de servicio. El permiso exigido no se revela (D3); se registra en el log del servidor."""
    if not identity.technical:
        logger.warning(
            "Identidad técnica exigida sujeto=%s metodo=%s ruta=%s", identity.subject, request.method, request.url.path
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_DETAIL)
    return identity


def _decimal(value: Decimal | None, places: int | None = None) -> str | None:
    if value is None:
        return None
    if places is not None:
        return format(Decimal(value).quantize(Decimal(1).scaleb(-places)), "f")
    return format(Decimal(value).normalize(), "f")


def application_responses(repository, applications) -> list[AutomaticPriceApplicationResponse]:
    requests = repository.requests_of(applications)
    currencies = repository.currencies_of(applications)
    items = []
    for application in applications:
        request = requests[application.request_id]
        places = currency_places(currencies[application.price_list_id])
        items.append(
            AutomaticPriceApplicationResponse(
                id=application.id,
                company_id=application.company_id,
                request_id=application.request_id,
                purchase_id=request.purchase_id,
                purchase_detail_id=request.purchase_detail_id,
                price_list_id=application.price_list_id,
                company_product_id=request.company_product_id,
                company_product_presentation_id=application.company_product_presentation_id,
                sequence=application.sequence,
                received_at=request.received_at,
                received_by_user_id=request.received_by_user_id,
                policy_id=application.policy_id,
                markup_percentage=_decimal(application.markup_percentage, 4),
                current_unit_cost=_decimal(application.current_unit_cost),
                previous_unit_cost=_decimal(application.previous_unit_cost),
                reference_cost=_decimal(application.reference_cost),
                previous_price=_decimal(application.previous_price, places),
                new_price=_decimal(application.new_price, places),
                previous_price_item_id=application.previous_price_item_id,
                new_price_item_id=application.new_price_item_id,
                cancelled_future_item_ids=list(application.cancelled_future_item_ids or []),
                status=application.status,
                attempts=application.attempts,
                next_attempt_at=application.next_attempt_at,
                last_error_code=application.last_error_code,
                first_attempt_at=application.first_attempt_at,
                completed_at=application.completed_at,
                resolved_by=application.resolved_by,
                resolution_reason=application.resolution_reason,
                version=application.version,
                created_at=application.created_at,
                updated_at=application.updated_at,
            )
        )
    return items


def _owned(repository, company_id: UUID, application_id: UUID):
    """La aplicación de la empresa de la ruta; una ajena o inexistente responde `404` (aislamiento)."""
    application = repository.get(application_id)
    if application is None or application.company_id != company_id:
        raise NotFoundError
    return application


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(tags=[TAG_PRICING_POLICIES])

    @router.post(
        "/companies/{company_id}/automatic-price-update-requests",
        response_model=PriceUpdateRequestAccepted,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[auth.permission(SERVICE, "automatic_price_update_requests", "submit")],
        summary="Recibir la solicitud de actualización de precio de una recepción (solo identidad técnica de Purchase)",
    )
    def submit_request(
        company_id: UUID,
        body: PriceUpdateRequestIn,
        actor: CurrentSubject,
        _identity: RequestIdentity = Depends(require_technical_identity),
        service: AutomaticPriceRequestService = Depends(get_automatic_price_request_service),
    ):
        request, applications = service.submit(company_id, body.model_dump(), actor=actor)
        return PriceUpdateRequestAccepted(
            request_id=request.id,
            applications=[ApplicationSummary.model_validate(application) for application in applications],
        )

    @router.get(
        APPLICATIONS,
        response_model=PaginatedResponse[AutomaticPriceApplicationResponse],
        dependencies=[auth.permission(SERVICE, "automatic_price_applications", "read")],
        summary="Listar las actualizaciones automáticas de precio (solo administradores y supervisores)",
    )
    def list_applications(
        company_id: UUID = Depends(company_dependency(write=False)),
        pagination: PaginationParams = Depends(),
        status_filter: str | None = Query(default=None, alias="status", pattern=STATUS_PATTERN),
        price_list_id: UUID | None = Query(default=None),
        company_product_presentation_id: UUID | None = Query(default=None),
        purchase_id: UUID | None = Query(default=None),
        repository=Depends(get_automatic_price_application_repository),
    ):
        page = repository.list_for_company(
            company_id,
            status=status_filter,
            price_list_id=price_list_id,
            presentation_id=company_product_presentation_id,
            purchase_id=purchase_id,
            page=pagination.page,
            page_size=pagination.page_size,
        )
        return PaginatedResponse[AutomaticPriceApplicationResponse](
            items=application_responses(repository, page.items),
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.get(
        APPLICATIONS + "/{application_id}",
        response_model=AutomaticPriceApplicationResponse,
        dependencies=[auth.permission(SERVICE, "automatic_price_applications", "read")],
        summary="Consultar una actualización automática de precio con su trazabilidad",
    )
    def get_application(
        application_id: UUID,
        company_id: UUID = Depends(company_dependency(write=False)),
        repository=Depends(get_automatic_price_application_repository),
    ):
        return application_responses(repository, [_owned(repository, company_id, application_id)])[0]

    @router.post(
        APPLICATIONS + "/{application_id}/resolution",
        response_model=AutomaticPriceApplicationResponse,
        dependencies=[auth.permission(SERVICE, "automatic_price_applications", "resolve")],
        summary="Resolver administrativamente una actualización pendiente o fallida (no modifica precios)",
    )
    def resolve_application(
        application_id: UUID,
        body: ApplicationResolution,
        actor: CurrentSubject,
        company_id: UUID = Depends(company_dependency(write=True)),
        repository=Depends(get_automatic_price_application_repository),
        service: AutomaticPriceResolutionService = Depends(get_automatic_price_resolution_service),
    ):
        current = _owned(repository, company_id, application_id)
        model = service.resolve(current, version=body.version, reason=body.reason, actor=actor)
        return application_responses(repository, [model])[0]

    return router
