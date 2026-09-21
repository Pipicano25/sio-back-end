"""Endpoints HTTP para tipos globales de condición de pago."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sio_auth import CurrentSubject

from payment_reference_service.api.filters.global_payment_condition_types import (
    GlobalPaymentConditionTypeFilters,
)
from payment_reference_service.api.pagination import PaginationParams
from payment_reference_service.api.schemas.global_payment_condition_types import (
    GlobalPaymentConditionTypeCreate,
    GlobalPaymentConditionTypeResponse,
    GlobalPaymentConditionTypeUpdate,
)
from payment_reference_service.api.schemas.pagination import PaginatedResponse
from payment_reference_service.api.security import auth
from payment_reference_service.application.exceptions import (
    GlobalPaymentConditionTypeConflictError,
    GlobalPaymentConditionTypeNotFoundError,
)
from payment_reference_service.application.global_payment_condition_types import (
    GlobalPaymentConditionTypeService,
)
from payment_reference_service.domain.global_payment_condition_types import (
    GlobalPaymentConditionType,
)
from payment_reference_service.infrastructure.database import get_db_session
from payment_reference_service.infrastructure.global_payment_condition_types_repository import (
    SqlAlchemyGlobalPaymentConditionTypeRepository,
)


SERVICE_PERMISSION = "payment_reference"
RESOURCE_PERMISSION = "global_payment_condition_types"


router = APIRouter(
    prefix="/global-payment-condition-types",
    tags=["global-payment-condition-types"],
)


def _get_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> GlobalPaymentConditionTypeService:
    """Construye el servicio de aplicación para la solicitud actual.

    Args:
        session: Sesión SQLAlchemy asociada a la solicitud.

    Returns:
        Servicio de aplicación configurado con su repositorio.
    """
    repository = SqlAlchemyGlobalPaymentConditionTypeRepository(session)

    return GlobalPaymentConditionTypeService(repository)


def _to_response(
    entity: GlobalPaymentConditionType,
) -> GlobalPaymentConditionTypeResponse:
    """Convierte una entidad de dominio en respuesta HTTP.

    Args:
        entity: Entidad que debe serializarse.

    Returns:
        Schema HTTP correspondiente.
    """
    return GlobalPaymentConditionTypeResponse.model_validate(entity)


@router.get(
    "",
    response_model=PaginatedResponse[GlobalPaymentConditionTypeResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar tipos globales de condición de pago",
    dependencies=[
        auth.permission(
            SERVICE_PERMISSION,
            RESOURCE_PERMISSION,
            "read",
        )
    ],
)
def list_global_payment_condition_types(
    pagination: Annotated[PaginationParams, Depends()],
    filters: Annotated[GlobalPaymentConditionTypeFilters, Depends()],
    service: Annotated[GlobalPaymentConditionTypeService, Depends(_get_service)],
) -> PaginatedResponse[GlobalPaymentConditionTypeResponse]:
    """Lista condiciones globales de pago de forma paginada.

    Permite búsqueda general en código, nombre y descripción, además de
    filtro exacto por estado.

    Args:
        pagination: Parámetros de página y tamaño de página.
        filters: Búsqueda y filtros HTTP.
        service: Servicio de aplicación.

    Returns:
        Página de tipos globales de condición de pago.
    """
    result = service.list(
        page=pagination.page,
        page_size=pagination.page_size,
        search=filters.search,
        status=filters.status,
    )

    return PaginatedResponse(
        items=[_to_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total_records=result.total_records,
        total_pages=result.total_pages,
    )


@router.get(
    "/{condition_type_id}",
    response_model=GlobalPaymentConditionTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar un tipo global de condición de pago",
    dependencies=[
        auth.permission(
            SERVICE_PERMISSION,
            RESOURCE_PERMISSION,
            "read",
        )
    ],
)
def get_global_payment_condition_type(
    condition_type_id: UUID,
    service: Annotated[GlobalPaymentConditionTypeService, Depends(_get_service)],
) -> GlobalPaymentConditionTypeResponse:
    """Obtiene una condición global de pago mediante su UUID.

    Args:
        condition_type_id: Identificador del registro.
        service: Servicio de aplicación.

    Returns:
        Tipo global de condición de pago encontrado.

    Raises:
        HTTPException: Si el registro no existe.
    """
    try:
        entity = service.get_by_id(condition_type_id)
    except GlobalPaymentConditionTypeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _to_response(entity)


@router.post(
    "",
    response_model=GlobalPaymentConditionTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un tipo global de condición de pago",
    dependencies=[
        auth.permission(
            SERVICE_PERMISSION,
            RESOURCE_PERMISSION,
            "create",
        )
    ],
)
def create_global_payment_condition_type(
    payload: GlobalPaymentConditionTypeCreate,
    actor_id: CurrentSubject,
    service: Annotated[GlobalPaymentConditionTypeService, Depends(_get_service)],
) -> GlobalPaymentConditionTypeResponse:
    """Crea un tipo global de condición de pago.

    La identidad utilizada para auditoría proviene del claim estable
    OIDC `sub` mediante `CurrentSubject`.

    Args:
        payload: Datos funcionales enviados por el cliente.
        actor_id: Subject OIDC del usuario autenticado.
        service: Servicio de aplicación.

    Returns:
        Registro creado.

    Raises:
        HTTPException: Si existe un conflicto de integridad.
    """
    try:
        entity = service.create(
            code=payload.code,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            actor_id=actor_id,
        )
    except GlobalPaymentConditionTypeConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _to_response(entity)


@router.put(
    "/{condition_type_id}",
    response_model=GlobalPaymentConditionTypeResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar completamente un tipo global de condición de pago",
    dependencies=[
        auth.permission(
            SERVICE_PERMISSION,
            RESOURCE_PERMISSION,
            "update",
        )
    ],
)
def update_global_payment_condition_type(
    condition_type_id: UUID,
    payload: GlobalPaymentConditionTypeUpdate,
    actor_id: CurrentSubject,
    service: Annotated[GlobalPaymentConditionTypeService, Depends(_get_service)],
) -> GlobalPaymentConditionTypeResponse:
    """Actualiza completamente una condición global de pago.

    `created_by` y `created_at` permanecen intactos. `updated_by` se
    obtiene del usuario autenticado y `updated_at` se actualiza en el
    caso de uso.

    Args:
        condition_type_id: Identificador del registro.
        payload: Estado funcional completo solicitado.
        actor_id: Subject OIDC del usuario autenticado.
        service: Servicio de aplicación.

    Returns:
        Registro actualizado.

    Raises:
        HTTPException: Si el registro no existe o existe un conflicto.
    """
    try:
        entity = service.update(
            condition_type_id=condition_type_id,
            code=payload.code,
            name=payload.name,
            description=payload.description,
            status=payload.status,
            actor_id=actor_id,
        )
    except GlobalPaymentConditionTypeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GlobalPaymentConditionTypeConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _to_response(entity)


@router.delete(
    "/{condition_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un tipo global de condición de pago",
    dependencies=[
        auth.permission(
            SERVICE_PERMISSION,
            RESOURCE_PERMISSION,
            "delete",
        )
    ],
)
def delete_global_payment_condition_type(
    condition_type_id: UUID,
    service: Annotated[GlobalPaymentConditionTypeService, Depends(_get_service)],
) -> Response:
    """Elimina físicamente una condición global de pago.

    Args:
        condition_type_id: Identificador del registro.
        service: Servicio de aplicación.

    Returns:
        Respuesta HTTP sin contenido.

    Raises:
        HTTPException: Si el registro no existe.
    """
    try:
        service.delete(condition_type_id)
    except GlobalPaymentConditionTypeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)