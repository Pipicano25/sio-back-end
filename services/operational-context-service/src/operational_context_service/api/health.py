"""Endpoints públicos de salud de Operational Context Service."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from operational_context_service.infrastructure.database import Database


def build_router(database: Database) -> APIRouter:
    """Construye el router de salud del servicio.

    Args:
        database: Infraestructura de conexión a PostgreSQL.

    Returns:
        Router FastAPI con endpoints de liveness y readiness.
    """
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
        status_code=status.HTTP_200_OK,
        summary="Comprobar que el servicio está preparado",
    )
    def get_ready() -> dict[str, str]:
        """Comprueba que PostgreSQL está disponible.

        Returns:
            Estado de preparación del servicio.

        Raises:
            HTTPException: Si PostgreSQL no está disponible.
        """
        try:
            database.check_connection()

        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="La base de datos no está disponible.",
            ) from None

        return {"status": "ok"}

    return router
