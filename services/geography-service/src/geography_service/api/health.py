from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from geography_service.infrastructure.database import Database


def build_router(database: Database) -> APIRouter:
    router = APIRouter(
        prefix="/health",
        tags=["Salud"],
    )

    @router.get(
        "/live",
        summary="Comprobar que el servicio está vivo",
    )
    def live() -> dict[str, str]:
        return {
            "status": "ok",
        }

    @router.get(
        "/ready",
        summary="Comprobar que el servicio está listo",
    )
    def ready() -> dict[str, str]:
        try:
            database.check_connection()

        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="La base de datos no está disponible.",
            ) from None

        return {
            "status": "ok",
        }

    return router