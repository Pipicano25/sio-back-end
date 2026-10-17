"""Rutas de las políticas de precios de lista (spec 021, `contracts/commercial-relationship.md` §1).

- Colección y alta bajo la lista: `/companies/{company_id}/price-lists/{price_list_id}/pricing-policies`.
- Política por UUID: `/pricing-policies/{policy_id}` y sus acciones (convención de rutas de la 010).
- Permisos `perm:commercial-relationship:pricing_policies:{read,create,update,delete}`, solo para administradores y
  supervisores (FR-021-32a). Siempre con membresía en la empresa: no hay exención técnica (las respuestas exponen
  porcentajes internos).
- Cobertura (FR-021-35, §3b): `POST /companies/{company_id}/pricing-policies/coverage` con
  `perm:commercial-relationship:pricing_policy_coverage:read`. Admite la exención técnica (`platform:lookup`) porque
  solo responde si hay cobertura y en qué listas, sin porcentajes ni costos.
"""

from __future__ import annotations

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sio_auth import CurrentSubject, SIOAuth

from commercial_relationship_service.api.company_scope import company_dependency, load_scoped
from commercial_relationship_service.api.dependencies import (
    get_identity,
    get_presentation_repository,
    get_pricing_policy_repository,
    get_pricing_policy_service,
    get_scope_service,
)
from commercial_relationship_service.api.filters.common import normalize_search
from commercial_relationship_service.api.openapi import TAG_PRICING_POLICIES
from commercial_relationship_service.api.pagination import PaginationParams
from commercial_relationship_service.api.schemas.common import PaginatedResponse
from commercial_relationship_service.api.schemas.pricing_policy import (
    CoverageItemResponse,
    CoverageRequest,
    CoverageResponse,
    PercentageChange,
    PolicyDeactivation,
    PolicyPresentationResponse,
    PolicyTermResponse,
    PresentationsChange,
    PricingPolicyCreate,
    PricingPolicyRename,
    PricingPolicyResponse,
)
from commercial_relationship_service.application.company_scope import (
    SERVICE,
    CompanyScopeService,
    RequestIdentity,
)
from commercial_relationship_service.application.pricing_coverage_service import PricingCoverageService
from commercial_relationship_service.application.pricing_policy_service import PricingPolicyService
from commercial_relationship_service.domain.currency import validate_currency

RESOURCE = "pricing_policies"
COVERAGE_RESOURCE = "pricing_policy_coverage"
BASE = "/pricing-policies"


def _resource(*, write: bool, allow_inactive_company: bool = False):
    def dependency(
        policy_id: UUID,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        repository=Depends(get_pricing_policy_repository),
    ):
        return load_scoped(
            repository.get,
            policy_id,
            identity=identity,
            scope=scope,
            write=write,
            allow_inactive_company=allow_inactive_company,
        )

    return dependency


def responses(repository, models) -> list[PricingPolicyResponse]:
    ids = [model.id for model in models]
    markups = repository.last_markups(ids)
    current = repository.current_markups(ids)
    counts = repository.presentation_counts(ids)
    return [
        PricingPolicyResponse.model_validate(
            {
                **{key: getattr(model, key) for key in PricingPolicyResponse.model_fields if hasattr(model, key)},
                "markup_percentage": current.get(model.id, markups.get(model.id)),
                "presentation_count": counts.get(model.id, 0),
            }
        )
        for model in models
    ]


def build_router(auth: SIOAuth) -> APIRouter:
    """Construye el router de políticas de precios."""
    router = APIRouter(tags=[TAG_PRICING_POLICIES])

    def permission(action: str):
        return auth.permission(SERVICE, RESOURCE, action)

    def one(repository, model) -> PricingPolicyResponse:
        return responses(repository, [model])[0]

    @router.post(
        "/companies/{company_id}" + BASE + "/coverage",
        response_model=CoverageResponse,
        dependencies=[auth.permission(SERVICE, COVERAGE_RESOURCE, "read")],
        summary="Consultar si las presentaciones tienen política de ganancia aplicable (sin porcentajes)",
    )
    def coverage(
        company_id: UUID,
        body: CoverageRequest,
        identity: RequestIdentity = Depends(get_identity),
        scope: CompanyScopeService = Depends(get_scope_service),
        repository=Depends(get_pricing_policy_repository),
        presentations=Depends(get_presentation_repository),
    ):
        currency = validate_currency(body.currency_code)
        items = PricingCoverageService(repository, presentations).coverage(
            company_id, currency, body.company_product_presentation_ids, identity=identity, scope=scope
        )
        return CoverageResponse(items=[CoverageItemResponse(**asdict(item)) for item in items])

    @router.get(
        "/companies/{company_id}/price-lists/{price_list_id}" + BASE,
        response_model=PaginatedResponse[PricingPolicyResponse],
        dependencies=[permission("read")],
        summary="Listar las políticas de ganancia de una lista de precios",
    )
    def list_policies(
        price_list_id: UUID,
        company_id: UUID = Depends(company_dependency(write=False)),
        pagination: PaginationParams = Depends(),
        status_filter: str | None = Query(default=None, alias="status", pattern="^(ACTIVE|INACTIVE|ALL)$"),
        search: str | None = Query(default=None, max_length=100),
        repository=Depends(get_pricing_policy_repository),
    ):
        page = repository.list_for_price_list(
            company_id,
            price_list_id,
            status=status_filter,
            search=normalize_search(search),
            page=pagination.page,
            page_size=pagination.page_size,
        )
        return PaginatedResponse[PricingPolicyResponse](
            items=responses(repository, page.items),
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.post(
        "/companies/{company_id}/price-lists/{price_list_id}" + BASE,
        response_model=PricingPolicyResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[permission("create")],
        summary="Crear una política de ganancia en una lista (no modifica precios)",
    )
    def create_policy(
        price_list_id: UUID,
        body: PricingPolicyCreate,
        response: Response,
        actor: CurrentSubject,
        company_id: UUID = Depends(company_dependency(write=True)),
        service: PricingPolicyService = Depends(get_pricing_policy_service),
        repository=Depends(get_pricing_policy_repository),
    ):
        model = service.create(company_id, price_list_id, body.model_dump(), actor=actor)
        response.headers["Location"] = f"/api/v1{BASE}/{model.id}"
        return one(repository, model)

    @router.get(
        BASE + "/{policy_id}",
        response_model=PricingPolicyResponse,
        dependencies=[permission("read")],
        summary="Consultar una política de ganancia",
    )
    def get_policy(current=Depends(_resource(write=False)), repository=Depends(get_pricing_policy_repository)):
        return one(repository, current)

    @router.get(
        BASE + "/{policy_id}/terms",
        response_model=list[PolicyTermResponse],
        dependencies=[permission("read")],
        summary="Historial de porcentajes de una política",
    )
    def list_terms(current=Depends(_resource(write=False)), repository=Depends(get_pricing_policy_repository)):
        return [PolicyTermResponse.model_validate(term) for term in repository.terms(current.id)]

    @router.get(
        BASE + "/{policy_id}/presentations",
        response_model=PaginatedResponse[PolicyPresentationResponse],
        dependencies=[permission("read")],
        summary="Presentaciones de una política (vigentes o, con include_closed, todo su historial)",
    )
    def list_presentations(
        current=Depends(_resource(write=False)),
        pagination: PaginationParams = Depends(),
        include_closed: bool = Query(default=False),
        repository=Depends(get_pricing_policy_repository),
    ):
        page = repository.assignments_page(
            current.id, include_closed=include_closed, page=pagination.page, page_size=pagination.page_size
        )
        return PaginatedResponse[PolicyPresentationResponse](
            items=[PolicyPresentationResponse.model_validate(item) for item in page.items],
            page=page.page,
            page_size=page.page_size,
            total_records=page.total_records,
            total_pages=page.total_pages,
        )

    @router.put(
        BASE + "/{policy_id}",
        response_model=PricingPolicyResponse,
        dependencies=[permission("update")],
        summary="Renombrar una política",
    )
    def rename_policy(
        body: PricingPolicyRename,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: PricingPolicyService = Depends(get_pricing_policy_service),
        repository=Depends(get_pricing_policy_repository),
    ):
        return one(repository, service.rename(current, name=body.name, version=body.version, actor=actor))

    @router.post(
        BASE + "/{policy_id}/percentage",
        response_model=PricingPolicyResponse,
        dependencies=[permission("update")],
        summary="Cambiar el porcentaje de una política (rige desde la siguiente recepción)",
    )
    def change_percentage(
        body: PercentageChange,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: PricingPolicyService = Depends(get_pricing_policy_service),
        repository=Depends(get_pricing_policy_repository),
    ):
        model = service.change_percentage(
            current, markup_percentage=body.markup_percentage, version=body.version, actor=actor
        )
        return one(repository, model)

    @router.post(
        BASE + "/{policy_id}/presentations",
        response_model=PricingPolicyResponse,
        dependencies=[permission("update")],
        summary="Asignar presentaciones a una política (hasta 100)",
    )
    def assign_presentations(
        body: PresentationsChange,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: PricingPolicyService = Depends(get_pricing_policy_service),
        repository=Depends(get_pricing_policy_repository),
    ):
        model = service.assign(
            current, presentation_ids=body.company_product_presentation_ids, version=body.version, actor=actor
        )
        return one(repository, model)

    @router.post(
        BASE + "/{policy_id}/presentations/remove",
        response_model=PricingPolicyResponse,
        dependencies=[permission("update")],
        summary="Retirar presentaciones de una política (hasta 100)",
    )
    def remove_presentations(
        body: PresentationsChange,
        actor: CurrentSubject,
        current=Depends(_resource(write=True)),
        service: PricingPolicyService = Depends(get_pricing_policy_service),
        repository=Depends(get_pricing_policy_repository),
    ):
        model = service.remove(
            current, presentation_ids=body.company_product_presentation_ids, version=body.version, actor=actor
        )
        return one(repository, model)

    @router.post(
        BASE + "/{policy_id}/deactivate",
        response_model=PricingPolicyResponse,
        dependencies=[permission("delete")],
        summary="Inactivar una política (estado final; no se reactiva)",
    )
    def deactivate_policy(
        body: PolicyDeactivation,
        actor: CurrentSubject,
        current=Depends(_resource(write=True, allow_inactive_company=True)),
        service: PricingPolicyService = Depends(get_pricing_policy_service),
        repository=Depends(get_pricing_policy_repository),
    ):
        model = service.deactivate(current, reason=body.reason, version=body.version, actor=actor)
        return one(repository, model)

    return router
