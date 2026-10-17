"""Configuración de seguridad: la autenticación y autorización se delegan en `sio-auth` (Principio V)."""

from sio_auth import SIOAuth

SERVICE = "product-inventory-query"
"""Segmento de servicio de los permisos `perm:product-inventory-query:{recurso}:read` (FR-022-110)."""


def build_auth() -> SIOAuth:
    """Instancia de `SIOAuth` configurada desde variables de entorno."""
    return SIOAuth.from_env()
