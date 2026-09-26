"""Router HTTP para reglas de tipos de identificación.

Los errores de aplicación los traduce `api/errors.py`; este módulo no asigna
estados HTTP de error.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sio_auth import CurrentSubject, SIOAuth

from party_identity_service.api.dependencies import (
    get_identification_type_rule_service,
)
from party_identity_service.api.filters.identification_type_rule import (
    IdentificationTypeRuleFilters,
)
from party_identity_service.api.pagination import PaginationParams
from party_identity_service.api.schemas.identification_type_rule import (
    IdentificationTypeRuleCreate,
    IdentificationTypeRuleResponse,
    IdentificationTypeRuleUpdate,
    IdentificationTypeRuleVersionCreate,
)
from party_identity_service.api.schemas.pagination import PaginatedResponse
from party_identity_service.api.schemas.status_action import StatusActionRequest
from party_identity_service.application.identification_type_rule_service import (
    IDENTITY_FIELDS,
    SEMANTIC_FIELDS,
    IdentificationTypeRuleService,
)

SERVICE = "party-identity"
RESOURCE = "identification_type_rules"
BASE_PATH = "/identification-type-rules"


def build_router(
    auth: SIOAuth,
) -> APIRouter:
    """Construye el router de reglas de identificación."""
    router = APIRouter(
        prefix=BASE_PATH,
        tags=["Reglas de identificación"],
    )

    @router.get(
        "",
        response_model=PaginatedResponse[IdentificationTypeRuleResponse],
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar reglas de identificación",
    )
    def list_identification_type_rules(
        pagination: PaginationParams = Depends(),
        filters: IdentificationTypeRuleFilters = Depends(),
        service: IdentificationTypeRuleService = Depends(
            get_identification_type_rule_service,
        ),
    ) -> PaginatedResponse[IdentificationTypeRuleResponse]:
        """Obtiene una página filtrada de reglas."""
        result = service.list_all(
            page=pagination.page,
            page_size=pagination.page_size,
            party_kind=filters.party_kind,
            country_id=filters.country_id,
            identification_type=filters.identification_type,
            sigla=filters.sigla,
            is_active=filters.is_active,
        )

        return PaginatedResponse(
            items=result.items,
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.get(
        "/{rule_id}",
        response_model=IdentificationTypeRuleResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "read")],
        summary="Consultar una regla de identificación",
    )
    def get_identification_type_rule(
        rule_id: UUID,
        service: IdentificationTypeRuleService = Depends(
            get_identification_type_rule_service,
        ),
    ):
        """Obtiene una regla por identificador."""
        return service.get_by_id(rule_id)

    @router.post(
        "",
        response_model=IdentificationTypeRuleResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Crear una regla de identificación",
    )
    def create_identification_type_rule(
        payload: IdentificationTypeRuleCreate,
        actor_id: CurrentSubject,
        response: Response,
        service: IdentificationTypeRuleService = Depends(
            get_identification_type_rule_service,
        ),
    ):
        """Crea una regla activa."""
        rule = service.create(
            **payload.model_dump(),
            actor_id=actor_id,
        )
        response.headers["Location"] = f"/api/v1{BASE_PATH}/{rule.id}"

        return rule

    @router.put(
        "/{rule_id}",
        response_model=IdentificationTypeRuleResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "update")],
        summary="Modificar la descripción o el ejemplo de una regla",
    )
    def update_identification_type_rule(
        rule_id: UUID,
        payload: IdentificationTypeRuleUpdate,
        actor_id: CurrentSubject,
        service: IdentificationTypeRuleService = Depends(
            get_identification_type_rule_service,
        ),
    ):
        """Modifica solo la descripción y el ejemplo (FR-013).

        Cambiar patrón o edades exige `POST /{rule_id}/versions`.
        """
        sent = payload.model_fields_set

        return service.update(
            rule_id,
            expected_version=payload.version,
            number_pattern_description=payload.number_pattern_description,
            example_value=payload.example_value,
            requested_identity={
                field: getattr(payload, field)
                for field in IDENTITY_FIELDS
                if field in sent
            },
            requested_semantics={
                field: getattr(payload, field)
                for field in SEMANTIC_FIELDS
                if field in sent
            },
            actor_id=actor_id,
        )

    @router.post(
        "/{rule_id}/versions",
        response_model=IdentificationTypeRuleResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[auth.permission(SERVICE, RESOURCE, "create")],
        summary="Crear una nueva versión de una regla (la anterior queda histórica)",
    )
    def create_identification_type_rule_version(
        rule_id: UUID,
        payload: IdentificationTypeRuleVersionCreate,
        actor_id: CurrentSubject,
        response: Response,
        service: IdentificationTypeRuleService = Depends(
            get_identification_type_rule_service,
        ),
    ):
        """Cierra la regla vigente y crea su sucesora (DS-07)."""
        data = payload.model_dump()
        expected_version = data.pop("version")
        rule = service.create_version(
            rule_id,
            expected_version=expected_version,
            actor_id=actor_id,
            **data,
        )
        response.headers["Location"] = f"/api/v1{BASE_PATH}/{rule.id}"

        return rule

    @router.post(
        "/{rule_id}/deactivate",
        response_model=IdentificationTypeRuleResponse,
        dependencies=[auth.permission(SERVICE, RESOURCE, "delete")],
        summary="Retirar una regla de identificación (no elimina)",
    )
    def deactivate_identification_type_rule(
        rule_id: UUID,
        payload: StatusActionRequest,
        actor_id: CurrentSubject,
        service: IdentificationTypeRuleService = Depends(
            get_identification_type_rule_service,
        ),
    ):
        """Retira la regla conservándola como histórica (FR-014)."""
        return service.deactivate(
            rule_id,
            expected_version=payload.version,
            actor_id=actor_id,
        )

    return router
