"""API pública de sio-auth.

Los microservicios deben importar desde este módulo
en lugar de usar módulos internos.
"""

from .auth import SIOAuth
from .config import AuthSettings
from .dependencies import (
    CurrentClaims,
    CurrentSubject,
    get_current_claims,
    get_current_subject,
)
from .errors import (
    AuthConfigurationError,
    AuthenticationError,
    SIOAuthError,
)
from .models import SioPermission
from .tokens import TokenClaims


__all__ = [
    "AuthConfigurationError",
    "AuthenticationError",
    "AuthSettings",
    "CurrentClaims",
    "CurrentSubject",
    "SIOAuth",
    "SIOAuthError",
    "SioPermission",
    "TokenClaims",
    "get_current_claims",
    "get_current_subject",
]