"""Configuración de seguridad de Party Identity Service.

La autenticación y autorización se delegan completamente en la
librería compartida `sio-auth`.
"""

from sio_auth import SIOAuth


def build_auth() -> SIOAuth:
    """Construye la fachada de autenticación del servicio.

    Returns:
        Instancia de `SIOAuth` configurada desde variables de entorno.
    """
    return SIOAuth.from_env()
