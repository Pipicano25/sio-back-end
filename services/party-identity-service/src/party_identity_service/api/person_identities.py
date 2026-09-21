"""Router HTTP para identidades globales de personas."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from party_identity_service.api.filters.person_identity import (
    PersonIdentityFilters,
)
from party_identity_service.api.pagination import PaginationParams
from party_identity_service.api.schemas.pagination import PaginatedResponse
from party_identity_service.api.schemas.person_identity import (
    PersonIdentityCreate,
    PersonIdentityResponse,
    PersonIdentityUpdate,
)
from party_identity_service.application.exceptions import (
    InvalidIdentificationNumberError,
    PersonIdentityConflictError,
    PersonIdentityNotFoundError,
    PersonIdentityVersionConflictError,
)
from party_identity_service.application.identification_rules import (
    build_identification_rule_set,
)
from party_identity_service.application.person_identity_service import (
    PersonIdentityService,
)
from party_identity_service.infrastructure.database import get_db_session
from party_identity_service.infrastructure.person_identity_repository import (
    SQLAlchemyPersonIdentityRepository,
)


def get_person_identity_service(
    request: Request,
    session: Session = Depends(get_db_session),
) -> PersonIdentityService:
    """Construye el servicio de aplicación para personas.

    Args:
        session: Sesión SQLAlchemy de la solicitud.

    Returns:
        Servicio de aplicación configurado.
    """
    repository = SQLAlchemyPersonIdentityRepository(
        session,
    )
    settings = request.app.state.settings
    identification_rules = build_identification_rule_set(
        colombia_country_id=settings.colombia_country_id,
    )

    return PersonIdentityService(
        repository,
        identification_rules,
    )


def build_router(
    auth: SIOAuth,
) -> APIRouter:
    """Construye el router de identidades de personas."""
    router = APIRouter(
        prefix="/person-identities",
        tags=["Identidades de personas"],
    )

    @router.get(
        "",
        response_model=PaginatedResponse[PersonIdentityResponse],
        dependencies=[
            auth.permission(
                "party-identity",
                "person_identities",
                "read",
            )
        ],
        summary="Consultar identidades de personas",
    )
    def list_person_identities(
        pagination: PaginationParams = Depends(),
        filters: PersonIdentityFilters = Depends(),
        service: PersonIdentityService = Depends(
            get_person_identity_service,
        ),
    ) -> PaginatedResponse[PersonIdentityResponse]:
        """Obtiene una página filtrada de identidades de persona."""
        result = service.list_all(
            page=pagination.page,
            page_size=pagination.page_size,
            search=filters.search,
            identification_country_id=filters.identification_country_id,
            identification_type=filters.identification_type,
            verification_status=filters.verification_status,
        )

        return PaginatedResponse(
            items=result.items,
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.get(
        "/{person_identity_id}",
        response_model=PersonIdentityResponse,
        dependencies=[
            auth.permission(
                "party-identity",
                "person_identities",
                "read",
            )
        ],
        summary="Consultar una identidad de persona",
    )
    def get_person_identity(
        person_identity_id: UUID,
        service: PersonIdentityService = Depends(
            get_person_identity_service,
        ),
    ):
        """Obtiene una identidad de persona por identificador."""
        try:
            return service.get_by_id(
                person_identity_id,
            )

        except PersonIdentityNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La persona solicitada no existe.",
            ) from None

    @router.post(
        "",
        response_model=PersonIdentityResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            auth.permission(
                "party-identity",
                "person_identities",
                "create",
            )
        ],
        summary="Crear una identidad de persona",
    )
    def create_person_identity(
        payload: PersonIdentityCreate,
        actor_id: CurrentSubject,
        service: PersonIdentityService = Depends(
            get_person_identity_service,
        ),
    ):
        """Crea una identidad global de persona."""
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

        except PersonIdentityConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

    @router.put(
        "/{person_identity_id}",
        response_model=PersonIdentityResponse,
        dependencies=[
            auth.permission(
                "party-identity",
                "person_identities",
                "update",
            )
        ],
        summary="Actualizar una identidad de persona",
    )
    def update_person_identity(
        person_identity_id: UUID,
        payload: PersonIdentityUpdate,
        actor_id: CurrentSubject,
        service: PersonIdentityService = Depends(
            get_person_identity_service,
        ),
    ):
        """Actualiza completamente una identidad global de persona."""
        data = payload.model_dump()
        expected_version = data.pop(
            "version",
        )

        try:
            return service.update(
                person_identity_id,
                expected_version=expected_version,
                actor_id=actor_id,
                **data,
            )

        except InvalidIdentificationNumberError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from None

        except PersonIdentityNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La persona solicitada no existe.",
            ) from None

        except (
            PersonIdentityConflictError,
            PersonIdentityVersionConflictError,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

    return router
