"""API pública de sio-auth.

Los microservicios deben importar desde este módulo
en lugar de usar módulos internos.
"""

from .auth import (
    DENIED_PERMISSION_ATTRIBUTE,
    FORBIDDEN_DETAIL,
    LOGGER_NAME,
    SIOAuth,
)
from .config import AuthSettings
from .cors import install_cors
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
from .permissions import evaluate_permission
from .tokens import TokenClaims


__all__ = [
    "DENIED_PERMISSION_ATTRIBUTE",
    "FORBIDDEN_DETAIL",
    "LOGGER_NAME",
    "AuthConfigurationError",
    "AuthenticationError",
    "AuthSettings",
    "CurrentClaims",
    "CurrentSubject",
    "SIOAuth",
    "SIOAuthError",
    "SioPermission",
    "evaluate_permission",
    "install_cors",
    "TokenClaims",
    "get_current_claims",
    "get_current_subject",
]