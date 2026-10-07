"""Endpoints públicos de salud (`contracts/rest-api.md`).

`/health/live` comprueba solo el proceso; `/health/ready` comprueba solo la base
de datos propia: nunca consulta a los proveedores.
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from purchase_service.infrastructure.database import Database


def build_router(database: Database) -> APIRouter:
    """Construye el router de salud del servicio."""
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/live", status_code=status.HTTP_200_OK, summary="Comprobar que el servicio está vivo")
    def get_live() -> dict[str, str]:
        """Proceso HTTP disponible; no valida dependencias."""
        return {"status": "ok"}

    @router.get("/ready", summary="Comprobar que el servicio está preparado")
    def get_ready() -> JSONResponse:
        """Base de datos disponible; `503` sin detalles internos si no lo está."""
        try:
            database.check_connection()
        except SQLAlchemyError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready"},
            )

        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})

    return router
