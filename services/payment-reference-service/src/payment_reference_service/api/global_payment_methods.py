"""Endpoints HTTP para métodos globales de pago.

Sin borrado físico (D7; spec 020, GAP-PR-18): un método usado en compras o ventas no puede
desaparecer. Se inactiva con `PUT` (`status = INACTIVE`).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sio_auth import CurrentSubject

from payment_reference_service.api.filters.global_payment_methods import (
    GlobalPaymentMethodFilters,
)
from payment_reference_service.api.pagination import PaginationParams
from payment_reference_service.api.schemas.global_payment_methods import (
    GlobalPaymentMethodCreate,
    GlobalPaymentMethodResponse,
    GlobalPaymentMethodUpdate,
)
from payment_reference_service.api.schemas.pagination import PaginatedResponse
from payment_reference_service.api.security import auth
from payment_reference_service.application.exceptions import (
    GlobalPaymentMethodConflictError,
    GlobalPaymentMethodNotFoundError,
)
from payment_reference_service.application.global_payment_methods import (
    GlobalPaymentMethodService,
)
from payment_reference_service.domain.global_payment_methods import (
    GlobalPaymentMethod,
)
from payment_reference_service.infrastructure.database import get_db_session
from payment_reference_service.infrastructure.global_payment_methods_repository import (
    SqlAlchemyGlobalPaymentMethodRepository,
)


SERVICE_PERMISSION = "payment-reference"
RESOURCE_PERMISSION = "global_payment_methods"


router = APIRouter(
    prefix="/global-payment-methods",
    tags=["global-payment-methods"],
)


def _get_service(
    session: Annotated[Session, Depends(get_db_session)],
) -> GlobalPaymentMethodService:
    """Construye el servicio de aplicación de la solicitud.

    Args:
        session: Sesión SQLAlchemy activa.

    Returns:
        Servicio de aplicación configurado.
    """
    repository = SqlAlchemyGlobalPaymentMethodRepository(session)

    return GlobalPaymentMethodService(repository)


def _to_response(
    entity: GlobalPaymentMethod,
) -> GlobalPaymentMethodResponse:
    """Convierte una entidad en respuesta HTTP.

    Args:
        entity: Entidad de dominio.

    Returns:
        Schema HTTP correspondiente.
    """
    return GlobalPaymentMethodResponse.model_validate(entity)


@router.get(
    "",
    response_model=PaginatedResponse[GlobalPaymentMethodResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar métodos globales de pago",
    dependencies=[
        auth.permission(
            SERVICE_PERMISSION,
            RESOURCE_PERMISSION,
            "read",
        )
    ],
)
def list_global_payment_methods(
    pagination: Annotated[PaginationParams, Depends()],
    filters: Annotated[GlobalPaymentMethodFilters, Depends()],
    service: Annotated[GlobalPaymentMethodService, Depends(_get_service)],
) -> PaginatedResponse[GlobalPaymentMethodResponse]:
    """Lista métodos globales de pago.

    Args:
        pagination: Parámetros de paginación.
        filters: Búsqueda y filtros HTTP.
        service: Servicio de aplicación.

    Returns:
        Página de métodos globales de pago.
    """
    result = service.list(
        page=pagination.page,
        page_size=pagination.page_size,
        search=filters.search,
        status=filters.status,
        method_type=filters.method_type,
        requires_reference=filters.requires_reference,
    )

    return PaginatedResponse(
        items=[_to_response(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total_records=result.total_records,
        total_pages=result.total_pages,
    )


@router.get(
    "/{payment_method_id}",
    response_model=GlobalPaymentMethodResponse,
    status_code=status.HTTP_200_OK,
    summary="Consultar un método global de pago",
    dependencies=[
        auth.permission(
            SERVICE_PERMISSION,
            RESOURCE_PERMISSION,
            "read",
        )
    ],
)
def get_global_payment_method(
    payment_method_id: UUID,
    service: Annotated[GlobalPaymentMethodService, Depends(_get_service)],
) -> GlobalPaymentMethodResponse:
    """Obtiene un método global de pago mediante UUID.

    Args:
        payment_method_id: Identificador del registro.
        service: Servicio de aplicación.

    Returns:
        Método encontrado.

    Raises:
        HTTPException: Si el método no existe.
    """
    try:
        entity = service.get_by_id(payment_method_id)
    except GlobalPaymentMethodNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return _to_response(entity)


@router.post(
    "",
    response_model=GlobalPaymentMethodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un método global de pago",
    dependencies=[
        auth.permission(
            SERVICE_PERMISSION,
            RESOURCE_PERMISSION,
            "create",
        )
    ],
)
def create_global_payment_method(
    payload: GlobalPaymentMethodCreate,
    actor_id: CurrentSubject,
    service: Annotated[GlobalPaymentMethodService, Depends(_get_service)],
) -> GlobalPaymentMethodResponse:
    """Crea un método global de pago.

    Args:
        payload: Información funcional del método.
        actor_id: Subject OIDC del usuario autenticado.
        service: Servicio de aplicación.

    Returns:
        Método creado.

    Raises:
        HTTPException: Si existe un conflicto de integridad.
    """
    try:
        entity = service.create(
            code=payload.code,
            name=payload.name,
            method_type=payload.method_type,
            requires_reference=payload.requires_reference,
            status=payload.status,
            actor_id=actor_id,
        )
    except GlobalPaymentMethodConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _to_response(entity)


@router.put(
    "/{payment_method_id}",
    response_model=GlobalPaymentMethodResponse,
    status_code=status.HTTP_200_OK,
    summary="Actualizar completamente un método global de pago",
    dependencies=[
        auth.permission(
            SERVICE_PERMISSION,
            RESOURCE_PERMISSION,
            "update",
        )
    ],
)
def update_global_payment_method(
    payment_method_id: UUID,
    payload: GlobalPaymentMethodUpdate,
    actor_id: CurrentSubject,
    service: Annotated[GlobalPaymentMethodService, Depends(_get_service)],
) -> GlobalPaymentMethodResponse:
    """Actualiza completamente un método global de pago.

    Args:
        payment_method_id: Identificador del registro.
        payload: Estado funcional completo solicitado.
        actor_id: Subject OIDC del usuario autenticado.
        service: Servicio de aplicación.

    Returns:
        Método actualizado.

    Raises:
        HTTPException: Si no existe o hay un conflicto de integridad.
    """
    try:
        entity = service.update(
            payment_method_id=payment_method_id,
            code=payload.code,
            name=payload.name,
            method_type=payload.method_type,
            requires_reference=payload.requires_reference,
            status=payload.status,
            actor_id=actor_id,
        )
    except GlobalPaymentMethodNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except GlobalPaymentMethodConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return _to_response(entity)
