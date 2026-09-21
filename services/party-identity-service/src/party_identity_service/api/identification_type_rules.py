"""Router HTTP para reglas de tipos de identificación."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from party_identity_service.api.filters.identification_type_rule import (
    IdentificationTypeRuleFilters,
)
from party_identity_service.api.pagination import PaginationParams
from party_identity_service.api.schemas.identification_type_rule import (
    IdentificationTypeRuleCreate,
    IdentificationTypeRuleResponse,
    IdentificationTypeRuleUpdate,
)
from party_identity_service.api.schemas.pagination import PaginatedResponse
from party_identity_service.application.exceptions import (
    CountryNotFoundError,
    CountryValidationUnavailableError,
    IdentificationTypeRuleConflictError,
    IdentificationTypeRuleNotFoundError,
    IdentificationTypeRuleVersionConflictError,
)
from party_identity_service.application.identification_type_rule_service import (
    IdentificationTypeRuleService,
)
from party_identity_service.infrastructure.database import get_db_session
from party_identity_service.infrastructure.geography_country_validator import (
    HTTPGeographyCountryValidator,
)
from party_identity_service.infrastructure.identification_type_rule_repository import (
    SQLAlchemyIdentificationTypeRuleRepository,
)


def get_identification_type_rule_service(
    request: Request,
    session: Session = Depends(get_db_session),
) -> IdentificationTypeRuleService:
    """Construye el servicio de aplicación para reglas."""
    repository = SQLAlchemyIdentificationTypeRuleRepository(
        session,
    )
    country_validator = HTTPGeographyCountryValidator(
        base_url=request.app.state.settings.geography_service_base_url,
        authorization=request.headers.get(
            "authorization",
        ),
    )

    return IdentificationTypeRuleService(
        repository,
        country_validator,
    )


def build_router(
    auth: SIOAuth,
) -> APIRouter:
    """Construye el router de reglas de identificación."""
    router = APIRouter(
        prefix="/identification-type-rules",
        tags=["Reglas de tipos de identificación"],
    )

    @router.get(
        "",
        response_model=PaginatedResponse[IdentificationTypeRuleResponse],
        dependencies=[
            auth.permission(
                "party-identity",
                "identification_type_rules",
                "read",
            )
        ],
        summary="Consultar reglas de identificación",
    )
    def list_identification_type_rules(
        pagination: PaginationParams = Depends(),
        filters: IdentificationTypeRuleFilters = Depends(),
        service: IdentificationTypeRuleService = Depends(
            get_identification_type_rule_service,
        ),
    ) -> PaginatedResponse[IdentificationTypeRuleResponse]:
        """Obtiene una página filtrada de reglas de identificación."""
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
        dependencies=[
            auth.permission(
                "party-identity",
                "identification_type_rules",
                "read",
            )
        ],
        summary="Consultar una regla de identificación",
    )
    def get_identification_type_rule(
        rule_id: UUID,
        service: IdentificationTypeRuleService = Depends(
            get_identification_type_rule_service,
        ),
    ):
        """Obtiene una regla por identificador."""
        try:
            return service.get_by_id(
                rule_id,
            )

        except IdentificationTypeRuleNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La regla solicitada no existe.",
            ) from None

    @router.post(
        "",
        response_model=IdentificationTypeRuleResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            auth.permission(
                "party-identity",
                "identification_type_rules",
                "create",
            )
        ],
        summary="Crear una regla de identificación",
    )
    def create_identification_type_rule(
        payload: IdentificationTypeRuleCreate,
        actor_id: CurrentSubject,
        service: IdentificationTypeRuleService = Depends(
            get_identification_type_rule_service,
        ),
    ):
        """Crea una regla de identificación."""
        try:
            return service.create(
                **payload.model_dump(),
                actor_id=actor_id,
            )

        except IdentificationTypeRuleConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

        except CountryNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from None

        except CountryValidationUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from None

    @router.put(
        "/{rule_id}",
        response_model=IdentificationTypeRuleResponse,
        dependencies=[
            auth.permission(
                "party-identity",
                "identification_type_rules",
                "update",
            )
        ],
        summary="Actualizar una regla de identificación",
    )
    def update_identification_type_rule(
        rule_id: UUID,
        payload: IdentificationTypeRuleUpdate,
        actor_id: CurrentSubject,
        service: IdentificationTypeRuleService = Depends(
            get_identification_type_rule_service,
        ),
    ):
        """Actualiza completamente una regla de identificación."""
        data = payload.model_dump()
        expected_version = data.pop(
            "version",
        )

        try:
            return service.update(
                rule_id,
                expected_version=expected_version,
                actor_id=actor_id,
                **data,
            )

        except IdentificationTypeRuleNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La regla solicitada no existe.",
            ) from None

        except CountryNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from None

        except CountryValidationUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from None

        except (
            IdentificationTypeRuleConflictError,
            IdentificationTypeRuleVersionConflictError,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

    return router
