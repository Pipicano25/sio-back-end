"""Configuración de seguridad: la autenticación y autorización se delegan en `sio-auth` (Principio V)."""

from sio_auth import SIOAuth

SERVICE = "business-reporting"
"""Segmento de servicio de los permisos `perm:business-reporting:{recurso}:read` (spec 023)."""


def build_auth() -> SIOAuth:
    """Instancia de `SIOAuth` configurada desde variables de entorno."""
    return SIOAuth.from_env()
