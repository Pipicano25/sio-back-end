"""Fachada pública utilizada por los microservicios FastAPI de SIO."""

from __future__ import annotations

import logging
from collections.abc import Callable, Collection

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.params import Depends as DependsParam

from .config import AuthSettings
from .dependencies import get_current_claims
from .jwks import JWKSClient
from .middleware import SIOAuthMiddleware
from .models import SioPermission
from .permissions import has_permission
from .tokens import AccessTokenDecoder, TokenClaims

LOGGER_NAME = "sio_auth"
"""Logger donde sio-auth registra las denegaciones por permiso (con el permiso exigido)."""

DENIED_PERMISSION_ATTRIBUTE = "sio_required_permission"
"""Atributo del registro de log con el permiso exigido (texto `perm:...`), para pruebas."""

FORBIDDEN_DETAIL = (
    "Su usuario no tiene permiso para realizar esta operación. Si necesita acceso, "
    "solicítelo al administrador del sistema indicando el trace_id de esta respuesta."
)
"""`detail` de todo `403` por permiso: nunca nombra el permiso, el rol ni la regla."""

logger = logging.getLogger(LOGGER_NAME)


class SIOAuth:
    """API de alto nivel para autenticación y permisos en microservicios de SIO."""

    def __init__(
        self,
        settings: AuthSettings,
        *,
        jwks_client: JWKSClient | None = None,
    ) -> None:
        self.settings = settings
        self._jwks_client = jwks_client or JWKSClient(settings)
        self._owns_jwks_client = jwks_client is None
        self._decoder = AccessTokenDecoder(settings, self._jwks_client)

    @classmethod
    def from_env(cls) -> "SIOAuth":
        """Crea sio-auth utilizando las variables de entorno estándar SIO_AUTH_*."""

        return cls(AuthSettings.from_env())

    def protect(
        self,
        app: FastAPI,
        *,
        public_paths: Collection[str] = (),
    ) -> None:
        """Protege todas las rutas HTTP excepto las rutas públicas declaradas de forma exacta."""

        app.add_middleware(
            SIOAuthMiddleware,
            decoder=self._decoder,
            public_paths=frozenset(public_paths),
        )

    def require_permission(
        self,
        service: str,
        resource: str,
        action: str,
    ) -> Callable[[Request], TokenClaims]:
        """Devuelve los claims únicamente cuando Keycloak suministró un permiso compatible.

        Sin el permiso responde `403` con un `detail` descriptivo que **no** revela el
        permiso exigido (fallo de seguridad: enumeración de permisos). El permiso se
        registra solo en el log del servidor (`sio_auth`, nivel WARNING) para que
        soporte lo diagnostique con el `trace_id` de la respuesta.
        """

        required = SioPermission(service, resource, action)

        def dependency(request: Request) -> TokenClaims:
            claims = get_current_claims(request)
            if not has_permission(claims.permissions, required):
                logger.warning(
                    "Acceso denegado por permiso insuficiente sujeto=%s permiso_requerido=%s "
                    "metodo=%s ruta=%s",
                    claims.subject,
                    required,
                    request.method,
                    request.url.path,
                    extra={DENIED_PERMISSION_ATTRIBUTE: str(required)},
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=FORBIDDEN_DETAIL,
                )
            return claims

        return dependency

    def permission(
        self,
        service: str,
        resource: str,
        action: str,
    ) -> DependsParam:
        """Crea una dependencia de ruta para un permiso concreto."""

        return Depends(self.require_permission(service, resource, action))

    def close(self) -> None:
        """Cierra los recursos creados internamente por esta instancia de sio-auth."""

        if self._owns_jwks_client:
            self._jwks_client.close()
