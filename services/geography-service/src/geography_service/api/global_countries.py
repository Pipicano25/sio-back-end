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

from geography_service.api.schemas.global_country import (
    GlobalCountryCreate,
    GlobalCountryResponse,
    GlobalCountryUpdate,
)
from geography_service.application.exceptions import (
    GlobalCountryConflictError,
    GlobalCountryNotFoundError,
    GlobalCountryVersionConflictError,
)
from geography_service.application.global_country_service import (
    GlobalCountryService,
)
from geography_service.infrastructure.database import (
    get_db_session,
)
from geography_service.infrastructure.global_country_repository import (
    SQLAlchemyGlobalCountryRepository,
)
from geography_service.api.pagination import (
    PaginationParams,
)
from geography_service.api.schemas.pagination import (
    PaginatedResponse,
)
from geography_service.api.filters.global_country import (
    GlobalCountryFilters,
)

def get_global_country_service(
    session: Session = Depends(get_db_session),
) -> GlobalCountryService:
    repository = SQLAlchemyGlobalCountryRepository(
        session,
    )

    return GlobalCountryService(
        repository,
    )


def build_router(
    auth: SIOAuth,
) -> APIRouter:
    router = APIRouter(
        prefix="/global-countries",
        tags=["Países globales"],
    )

    @router.get(
        "",
        response_model=PaginatedResponse[
            GlobalCountryResponse
        ],
        dependencies=[
            auth.permission(
                "geography",
                "global_countries",
                "read",
            )
        ],
        summary="Consultar países globales",
    )
    def list_countries(
        pagination: PaginationParams = Depends(),
        filters: GlobalCountryFilters = Depends(),
        service: GlobalCountryService = Depends(
            get_global_country_service,
        ),
    ) -> PaginatedResponse[GlobalCountryResponse]:
        """Obtiene una página filtrada de países globales.

        Args:
            pagination: Configuración de paginación.
            filters: Filtros de países.
            service: Servicio de aplicación.

        Returns:
            Países globales paginados.
        """
        result = service.list_all(
            page=pagination.page,
            page_size=pagination.page_size,
            search=filters.search,
            iso2_code=filters.iso2_code,
            iso3_code=filters.iso3_code,
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
        "/{country_id}",
        response_model=GlobalCountryResponse,
        dependencies=[
            auth.permission(
                "geography",
                "global_countries",
                "read",
            )
        ],
        summary="Consultar un país global",
    )
    def get_country(
        country_id: UUID,
        service: GlobalCountryService = Depends(
            get_global_country_service,
        ),
    ):
        try:
            return service.get_by_id(
                country_id,
            )

        except GlobalCountryNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El país solicitado no existe.",
            ) from None

    @router.post(
        "",
        response_model=GlobalCountryResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            auth.permission(
                "geography",
                "global_countries",
                "create",
            )
        ],
        summary="Crear un país global",
    )
    def create_country(
        payload: GlobalCountryCreate,
        actor_id: CurrentSubject,
        service: GlobalCountryService = Depends(
            get_global_country_service,
        ),
    ):
        try:
            return service.create(
                **payload.model_dump(),
                actor_id=actor_id,
            )

        except GlobalCountryConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

    @router.put(
        "/{country_id}",
        response_model=GlobalCountryResponse,
        dependencies=[
            auth.permission(
                "geography",
                "global_countries",
                "update",
            )
        ],
        summary="Actualizar un país global",
    )
    def update_country(
        country_id: UUID,
        payload: GlobalCountryUpdate,
        actor_id: CurrentSubject,
        service: GlobalCountryService = Depends(
            get_global_country_service,
        ),
    ):
        data = payload.model_dump()

        expected_version = data.pop(
            "version",
        )

        try:
            return service.update(
                country_id,
                expected_version=expected_version,
                actor_id=actor_id,
                **data,
            )

        except GlobalCountryNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El país solicitado no existe.",
            ) from None

        except (
            GlobalCountryConflictError,
            GlobalCountryVersionConflictError,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

    @router.delete(
        "/{country_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[
            auth.permission(
                "geography",
                "global_countries",
                "delete",
            )
        ],
        summary="Eliminar un país global",
    )
    def delete_country(
        country_id: UUID,
        service: GlobalCountryService = Depends(
            get_global_country_service,
        ),
    ) -> Response:
        try:
            service.delete(
                country_id,
            )

        except GlobalCountryNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="El país solicitado no existe.",
            ) from None

        except GlobalCountryVersionConflictError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
        )

    return router