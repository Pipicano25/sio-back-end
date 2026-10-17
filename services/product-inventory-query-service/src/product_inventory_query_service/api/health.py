"""Endpoints públicos de salud (FR-022-78, Principio V).

- `/health/live`: solo el proceso.
- `/health/ready`: la configuración ya se validó al construir la aplicación; aquí se comprueba que
  el JWKS de Keycloak (clase B) responde. **Nunca** consulta CR, PC, Inventory ni OC (clase C): su
  caída se refleja como `503` por solicitud, no como "no listo".
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

ReadinessProbe = Callable[[], bool]
"""Devuelve `True` si el JWKS responde. No debe lanzar excepciones."""


def build_router(jwks_probe: ReadinessProbe) -> APIRouter:
    """Construye el router de salud del servicio."""
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/live", status_code=status.HTTP_200_OK, summary="Comprobar que el servicio está vivo")
    def get_live() -> dict[str, str]:
        """Proceso HTTP disponible; no valida dependencias."""
        return {"status": "ok"}

    @router.get("/ready", summary="Comprobar que el servicio está preparado")
    def get_ready() -> JSONResponse:
        """Configuración válida y JWKS disponible; `503` sin detalles internos si no lo está."""
        if not jwks_probe():
            return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"status": "not_ready"})

        return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})

    return router
