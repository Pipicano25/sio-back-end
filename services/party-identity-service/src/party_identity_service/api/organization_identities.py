"""Router HTTP para identidades globales de organizaciones."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from party_identity_service.api.filters.organization_identity import (
    OrganizationIdentityFilters,
)
from party_identity_service.api.pagination import PaginationParams
from party_identity_service.api.schemas.organization_identity import (
    OrganizationIdentityCreate,
    OrganizationIdentityResponse,
    OrganizationIdentityUpdate,
)
from party_identity_service.api.schemas.pagination import PaginatedResponse
from party_identity_service.application.exceptions import (
    CountryNotFoundError,
    CountryValidationUnavailableError,
    InvalidIdentificationNumberError,
    OrganizationIdentityConflictError,
    OrganizationIdentityNotFoundError,
    OrganizationIdentityVersionConflictError,
)
from party_identity_service.application.organization_identity_service import (
    OrganizationIdentityService,
)
from party_identity_service.infrastructure.database import get_db_session
from party_identity_service.infrastructure.geography_country_validator import (
    HTTPGeographyCountryValidator,
)
from party_identity_service.infrastructure.identification_type_rule_repository import (
    SQLAlchemyIdentificationTypeRuleRepository,
)
from party_identity_service.infrastructure.organization_identity_repository import (
    SQLAlchemyOrganizationIdentityRepository,
)


def get_organization_identity_service(
    request: Request,
    session: Session = Depends(get_db_session),
) -> OrganizationIdentityService:
    """Construye el servicio de aplicación para organizaciones."""
    repository = SQLAlchemyOrganizationIdentityRepository(
        session,
    )
    identification_rule_repository = SQLAlchemyIdentificationTypeRuleRepository(
        session,
    )
    country_validator = HTTPGeographyCountryValidator(
        base_url=request.app.state.settings.geography_service_base_url,
        authorization=request.headers.get(
            "authorization",
        ),
    )

    return OrganizationIdentityService(
        repository,
        identification_rule_repository,
        country_validator,
    )


def build_router(
    auth: SIOAuth,
) -> APIRouter:
    """Construye el router de identidades de organizaciones."""
    router = APIRouter(
        prefix="/organization-identities",
        tags=["Identidades de organizaciones"],
    )

    @router.get(
        "",
        response_model=PaginatedResponse[OrganizationIdentityResponse],
        dependencies=[
            auth.permission(
                "party-identity",
                "organization_identities",
                "read",
            )
        ],
        summary="Consultar identidades de organizaciones",
    )
    def list_organization_identities(
        pagination: PaginationParams = Depends(),
        filters: OrganizationIdentityFilters = Depends(),
        service: OrganizationIdentityService = Depends(
            get_organization_identity_service,
        ),
    ) -> PaginatedResponse[OrganizationIdentityResponse]:
        """Obtiene una página filtrada de identidades de organización."""
        result = service.list_all(
            page=pagination.page,
            page_size=pagination.page_size,
            search=filters.search,
            country_id=filters.country_id,
            identification_type=filters.identification_type,
            registration_status=filters.registration_status,
        )

        return PaginatedResponse(
            items=result.items,
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.get(
        "/{organization_identity_id}",
        response_model=OrganizationIdentityResponse,
        dependencies=[
            auth.permission(
                "party-identity",
                "organization_identities",
                "read",
            )
        ],
        summary="Consultar una identidad de organización",
    )
    def get_organization_identity(
        organization_identity_id: UUID,
        service: OrganizationIdentityService = Depends(
            get_organization_identity_service,
        ),
    ):
        """Obtiene una identidad de organización por identificador."""
        try:
            return service.get_by_id(
                organization_identity_id,
            )

        except OrganizationIdentityNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La organización solicitada no existe.",
            ) from None

    @router.post(
        "",
        response_model=OrganizationIdentityResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            auth.permission(
                "party-identity",
                "organization_identities",
                "create",
            )
        ],
        summary="Crear una identidad de organización",
    )
    def create_organization_identity(
        payload: OrganizationIdentityCreate,
        actor_id: CurrentSubject,
        service: OrganizationIdentityService = Depends(
            get_organization_identity_service,
        ),
    ):
        """Crea una identidad global de organización."""
        try:
            return service.create(
                **payload.model_dump(),
                actor_id=actor_id,
            )

        except InvalidIdentificationNumberError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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

        except OrganizationIdentityConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

    @router.put(
        "/{organization_identity_id}",
        response_model=OrganizationIdentityResponse,
        dependencies=[
            auth.permission(
                "party-identity",
                "organization_identities",
                "update",
            )
        ],
        summary="Actualizar una identidad de organización",
    )
    def update_organization_identity(
        organization_identity_id: UUID,
        payload: OrganizationIdentityUpdate,
        actor_id: CurrentSubject,
        service: OrganizationIdentityService = Depends(
            get_organization_identity_service,
        ),
    ):
        """Actualiza completamente una identidad global de organización."""
        data = payload.model_dump()
        expected_version = data.pop(
            "version",
        )

        try:
            return service.update(
                organization_identity_id,
                expected_version=expected_version,
                actor_id=actor_id,
                **data,
            )

        except InvalidIdentificationNumberError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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

        except OrganizationIdentityNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La organización solicitada no existe.",
            ) from None

        except (
            OrganizationIdentityConflictError,
            OrganizationIdentityVersionConflictError,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

    return router
