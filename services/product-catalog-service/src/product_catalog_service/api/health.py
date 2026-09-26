"""Endpoints públicos de salud de Product Catalog Service (Principio V)."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from product_catalog_service.infrastructure.database import Database


def build_router(database: Database) -> APIRouter:
    """Construye el router de salud del servicio."""
    router = APIRouter(
        prefix="/health",
        tags=["health"],
    )

    @router.get(
        "/live",
        status_code=status.HTTP_200_OK,
        summary="Comprobar que el proceso está vivo",
    )
    def get_live() -> dict[str, str]:
        """No consulta dependencias ni expone datos internos."""
        return {"status": "ok"}

    @router.get(
        "/ready",
        status_code=status.HTTP_200_OK,
        summary="Comprobar que el servicio está preparado",
        responses={503: {"description": "La base de datos no está disponible"}},
    )
    def get_ready():
        """Comprueba PostgreSQL sin exponer detalles internos."""
        try:
            database.ping()
        except SQLAlchemyError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready"},
            )

        return {"status": "ready"}

    return router
