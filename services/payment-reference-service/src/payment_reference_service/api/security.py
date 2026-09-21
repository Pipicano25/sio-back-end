"""Configuración de seguridad de Payment Reference Service.

La autenticación y autorización se delegan completamente en la
librería compartida `sio-auth`.
"""

from sio_auth import SIOAuth


auth = SIOAuth.from_env()