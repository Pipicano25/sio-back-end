"""Configuración de seguridad de Product Catalog Service.

La autenticación y autorización se delegan completamente en `sio-auth`.
Los permisos siguen el formato `perm:product-catalog:{recurso}:{accion}` (R-18).
"""

from fastapi.params import Depends as DependsParam
from sio_auth import SIOAuth

SERVICE_NAME = "product-catalog"


def build_auth() -> SIOAuth:
    """Construye la fachada de autenticación desde variables de entorno."""
    return SIOAuth.from_env()


def permission(
    auth: SIOAuth,
    resource: str,
    action: str,
) -> DependsParam:
    """Dependencia de ruta que exige `perm:product-catalog:{resource}:{action}`."""
    return auth.permission(SERVICE_NAME, resource, action)
