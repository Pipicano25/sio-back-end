"""Fachada pública utilizada por los microservicios FastAPI de SIO."""

from __future__ import annotations

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
        """Devuelve los claims únicamente cuando Keycloak suministró un permiso compatible."""

        required = SioPermission(service, resource, action)

        def dependency(request: Request) -> TokenClaims:
            claims = get_current_claims(request)
            if not has_permission(claims.permissions, required):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Falta el permiso requerido: {required}",
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
