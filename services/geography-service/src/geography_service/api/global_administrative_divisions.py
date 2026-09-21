from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sio_auth import CurrentSubject, SIOAuth
from sqlalchemy.orm import Session

from geography_service.api.schemas.global_administrative_division import (
    GlobalAdministrativeDivisionCreate,
    GlobalAdministrativeDivisionResponse,
    GlobalAdministrativeDivisionUpdate,
)
from geography_service.application.exceptions import (
    GlobalAdministrativeDivisionConflictError,
    GlobalAdministrativeDivisionInvalidParentError,
    GlobalAdministrativeDivisionNotFoundError,
    GlobalAdministrativeDivisionVersionConflictError,
)
from geography_service.application.global_administrative_division_service import (
    GlobalAdministrativeDivisionService,
)
from geography_service.infrastructure.database import get_db_session
from geography_service.infrastructure.global_administrative_division_repository import (
    SQLAlchemyGlobalAdministrativeDivisionRepository,
)
from geography_service.api.pagination import (
    PaginationParams,
)
from geography_service.api.schemas.pagination import (
    PaginatedResponse,
)
from geography_service.api.filters.global_administrative_division import (
    GlobalAdministrativeDivisionFilters,
)


def get_service(
    session: Session = Depends(get_db_session),
) -> GlobalAdministrativeDivisionService:
    return GlobalAdministrativeDivisionService(
        SQLAlchemyGlobalAdministrativeDivisionRepository(session)
    )


def build_router(auth: SIOAuth) -> APIRouter:
    router = APIRouter(
        prefix="/global-administrative-divisions",
        tags=["Divisiones administrativas globales"],
    )

    @router.get(
        "",
        response_model=PaginatedResponse[
            GlobalAdministrativeDivisionResponse
        ],
        dependencies=[
            auth.permission(
                "geography",
                "global_administrative_divisions",
                "read",
            )
        ],
    )
    def list_divisions(
        pagination: PaginationParams = Depends(),
        filters: GlobalAdministrativeDivisionFilters = Depends(),
        service: GlobalAdministrativeDivisionService = Depends(
            get_service,
        ),
    ):
        """Obtiene divisiones administrativas filtradas.

        Args:
            pagination: Configuración de paginación.
            filters: Filtros disponibles.
            service: Servicio de aplicación.

        Returns:
            Divisiones administrativas paginadas.
        """
        result = service.list_all(
            page=pagination.page,
            page_size=pagination.page_size,
            search=filters.search,
            country_id=filters.country_id,
            parent_division_id=filters.parent_division_id,
            division_type=filters.division_type,
            status=filters.status,
        )

        return PaginatedResponse(
            items=result.items,
            page=result.page,
            page_size=result.page_size,
            total_records=result.total_records,
            total_pages=result.total_pages,
        )

    @router.get(
        "/{division_id}",
        response_model=GlobalAdministrativeDivisionResponse,
        dependencies=[
            auth.permission(
                "geography",
                "global_administrative_divisions",
                "read",
            )
        ],
    )
    def get_division(
        division_id: UUID,
        service: GlobalAdministrativeDivisionService = Depends(get_service),
    ):
        try:
            return service.get_by_id(division_id)

        except GlobalAdministrativeDivisionNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="La división administrativa solicitada no existe.",
            ) from None

    @router.post(
        "",
        response_model=GlobalAdministrativeDivisionResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            auth.permission(
                "geography",
                "global_administrative_divisions",
                "create",
            )
        ],
    )
    def create_division(
        payload: GlobalAdministrativeDivisionCreate,
        actor_id: CurrentSubject,
        service: GlobalAdministrativeDivisionService = Depends(get_service),
    ):
        try:
            return service.create(
                **payload.model_dump(),
                actor_id=actor_id,
            )

        except (
            GlobalAdministrativeDivisionConflictError,
            GlobalAdministrativeDivisionInvalidParentError,
        ) as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from None

    @router.put(
        "/{division_id}",
        response_model=GlobalAdministrativeDivisionResponse,
        dependencies=[
            auth.permission(
                "geography",
                "global_administrative_divisions",
                "update",
            )
        ],
    )
    def update_division(
        division_id: UUID,
        payload: GlobalAdministrativeDivisionUpdate,
        actor_id: CurrentSubject,
        service: GlobalAdministrativeDivisionService = Depends(get_service),
    ):
        data = payload.model_dump()
        expected_version = data.pop("version")

        try:
            return service.update(
                division_id,
                expected_version=expected_version,
                actor_id=actor_id,
                **data,
            )

        except GlobalAdministrativeDivisionNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="La división administrativa solicitada no existe.",
            ) from None

        except (
            GlobalAdministrativeDivisionConflictError,
            GlobalAdministrativeDivisionInvalidParentError,
            GlobalAdministrativeDivisionVersionConflictError,
        ) as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from None

    @router.delete(
        "/{division_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[
            auth.permission(
                "geography",
                "global_administrative_divisions",
                "delete",
            )
        ],
    )
    def delete_division(
        division_id: UUID,
        service: GlobalAdministrativeDivisionService = Depends(get_service),
    ) -> Response:
        try:
            service.delete(division_id)

        except GlobalAdministrativeDivisionNotFoundError:
            raise HTTPException(
                status_code=404,
                detail="La división administrativa solicitada no existe.",
            ) from None

        except GlobalAdministrativeDivisionConflictError as exc:
            raise HTTPException(
                status_code=409,
                detail=str(exc),
            ) from None

        return Response(status_code=204)

    return router
