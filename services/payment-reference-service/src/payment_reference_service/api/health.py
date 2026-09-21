"""Endpoints públicos de salud de Payment Reference Service."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from payment_reference_service.infrastructure.database import (
    is_database_ready,
)

router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Comprobar que el servicio está vivo",
)
def get_live() -> dict[str, str]:
    """Comprueba que el proceso HTTP está disponible.

    Este endpoint no valida dependencias externas.

    Returns:
        Estado básico del proceso.
    """
    return {"status": "ok"}


@router.get(
    "/ready",
    summary="Comprobar que el servicio está preparado",
)
def get_ready() -> JSONResponse:
    """Comprueba la disponibilidad de PostgreSQL.

    Returns:
        Respuesta 200 cuando PostgreSQL se encuentra disponible o 503
        cuando la dependencia no responde.
    """
    if is_database_ready():
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok"},
        )

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "unavailable",
            "message": "PostgreSQL no está disponible.",
        },
    )