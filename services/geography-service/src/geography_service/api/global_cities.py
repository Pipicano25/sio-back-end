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

from geography_service.api.schemas.global_city import (
    GlobalCityCreate,
    GlobalCityResponse,
    GlobalCityUpdate,
)
from geography_service.application.exceptions import (
    GlobalCityConflictError,
    GlobalCityInvalidAdministrativeDivisionError,
    GlobalCityNotFoundError,
    GlobalCityVersionConflictError,
)
from geography_service.application.global_city_service import (
    GlobalCityService,
)
from geography_service.infrastructure.database import (
    get_db_session,
)
from geography_service.infrastructure.global_city_repository import (
    SQLAlchemyGlobalCityRepository,
)
from geography_service.api.pagination import (
    PaginationParams,
)
from geography_service.api.schemas.pagination import (
    PaginatedResponse,
)
from geography_service.api.filters.global_city import (
    GlobalCityFilters,
)


def get_global_city_service(
    session: Session = Depends(get_db_session),
) -> GlobalCityService:
    """Construye el servicio de aplicación para ciudades.

    Args:
        session: Sesión SQLAlchemy de la request actual.

    Returns:
        Servicio configurado con el repositorio SQLAlchemy.
    """
    repository = SQLAlchemyGlobalCityRepository(
        session,
    )

    return GlobalCityService(
        repository,
    )


def build_router(
    auth: SIOAuth,
) -> APIRouter:
    """Construye el router HTTP de ciudades globales.

    Args:
        auth: Instancia compartida de sio-auth utilizada para declarar
            permisos sobre los endpoints.

    Returns:
        Router FastAPI configurado.
    """
    router = APIRouter(
        prefix="/global-cities",
        tags=["Ciudades globales"],
    )

    @router.get(
        "",
        response_model=PaginatedResponse[
            GlobalCityResponse
        ],
        dependencies=[
            auth.permission(
                "geography",
                "global_cities",
                "read",
            )
        ],
        summary="Consultar ciudades globales",
    )
    def list_cities(
        pagination: PaginationParams = Depends(),
        filters: GlobalCityFilters = Depends(),
        service: GlobalCityService = Depends(
            get_global_city_service,
        ),
    ):
        """Obtiene ciudades globales filtradas.

        Args:
            pagination: Configuración de paginación.
            filters: Filtros disponibles para ciudades.
            service: Servicio de aplicación.

        Returns:
            Ciudades globales paginadas.
        """
        result = service.list_all(
            page=pagination.page,
            page_size=pagination.page_size,
            search=filters.search,
            country_id=filters.country_id,
            administrative_division_id=(
                filters.administrative_division_id
            ),
            code=filters.code,
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
        "/{city_id}",
        response_model=GlobalCityResponse,
        dependencies=[
            auth.permission(
                "geography",
                "global_cities",
                "read",
            )
        ],
        summary="Consultar una ciudad global",
    )
    def get_city(
        city_id: UUID,
        service: GlobalCityService = Depends(
            get_global_city_service,
        ),
    ):
        """Obtiene una ciudad global por identificador.

        Args:
            city_id: Identificador de la ciudad.
            service: Servicio de aplicación.

        Returns:
            Ciudad solicitada.

        Raises:
            HTTPException: Con 404 cuando la ciudad no existe.
        """
        try:
            return service.get_by_id(
                city_id,
            )

        except GlobalCityNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La ciudad solicitada no existe.",
            ) from None

    @router.post(
        "",
        response_model=GlobalCityResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            auth.permission(
                "geography",
                "global_cities",
                "create",
            )
        ],
        summary="Crear una ciudad global",
    )
    def create_city(
        payload: GlobalCityCreate,
        actor_id: CurrentSubject,
        service: GlobalCityService = Depends(
            get_global_city_service,
        ),
    ):
        """Crea una nueva ciudad global.

        Args:
            payload: Datos enviados por el cliente.
            actor_id: Subject del usuario autenticado.
            service: Servicio de aplicación.

        Returns:
            Ciudad creada.

        Raises:
            HTTPException: Con 409 ante conflictos de integridad.
        """
        try:
            return service.create(
                **payload.model_dump(),
                actor_id=actor_id,
            )

        except (
            GlobalCityConflictError,
            GlobalCityInvalidAdministrativeDivisionError,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

    @router.put(
        "/{city_id}",
        response_model=GlobalCityResponse,
        dependencies=[
            auth.permission(
                "geography",
                "global_cities",
                "update",
            )
        ],
        summary="Actualizar una ciudad global",
    )
    def update_city(
        city_id: UUID,
        payload: GlobalCityUpdate,
        actor_id: CurrentSubject,
        service: GlobalCityService = Depends(
            get_global_city_service,
        ),
    ):
        """Actualiza completamente una ciudad global.

        Args:
            city_id: Identificador de la ciudad.
            payload: Estado completo que debe quedar almacenado.
            actor_id: Subject del usuario autenticado.
            service: Servicio de aplicación.

        Returns:
            Ciudad actualizada.

        Raises:
            HTTPException: Con 404 si no existe o 409 ante conflictos.
        """
        data = payload.model_dump()

        expected_version = data.pop(
            "version",
        )

        try:
            return service.update(
                city_id,
                expected_version=expected_version,
                actor_id=actor_id,
                **data,
            )

        except GlobalCityNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La ciudad solicitada no existe.",
            ) from None

        except (
            GlobalCityConflictError,
            GlobalCityInvalidAdministrativeDivisionError,
            GlobalCityVersionConflictError,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

    @router.delete(
        "/{city_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[
            auth.permission(
                "geography",
                "global_cities",
                "delete",
            )
        ],
        summary="Eliminar una ciudad global",
    )
    def delete_city(
        city_id: UUID,
        service: GlobalCityService = Depends(
            get_global_city_service,
        ),
    ) -> Response:
        """Elimina físicamente una ciudad global.

        Args:
            city_id: Identificador de la ciudad.
            service: Servicio de aplicación.

        Returns:
            Respuesta HTTP sin contenido.

        Raises:
            HTTPException: Con 404 si no existe o 409 ante conflictos.
        """
        try:
            service.delete(
                city_id,
            )

        except GlobalCityNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="La ciudad solicitada no existe.",
            ) from None

        except (
            GlobalCityConflictError,
            GlobalCityVersionConflictError,
        ) as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(exc),
            ) from None

        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
        )

    return router
