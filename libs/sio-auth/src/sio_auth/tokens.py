"""Validación de tokens de acceso y claims de identidad de la solicitud."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping

import jwt

from .config import AuthSettings
from .errors import AuthenticationError
from .jwks import JWKSClient
from .models import SioGrant
from .permissions import extract_permission_grants


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Identidad validada extraída de un token de acceso de Keycloak."""

    subject: str
    issuer: str
    audiences: tuple[str, ...]
    expires_at: datetime
    roles: frozenset[str]
    permissions: frozenset[SioGrant]
    preferred_username: str | None
    email: str | None
    raw: Mapping[str, Any]

    @property
    def sub(self) -> str:
        """Alias compatible con JWT para ``subject``."""

        return self.subject

    @property
    def keycloak_user_id(self) -> str:
        """Alias semántico utilizado por el código de negocio de SIO."""

        return self.subject


class AccessTokenDecoder:
    """Valida tokens de acceso de Keycloak utilizando claves de firma obtenidas del JWKS real."""

    def __init__(self, settings: AuthSettings, jwks_client: JWKSClient) -> None:
        self._settings = settings
        self._jwks_client = jwks_client

    def decode(self, token: str) -> TokenClaims:
        if not isinstance(token, str) or not token.strip():
            raise AuthenticationError("El token de acceso Bearer está vacío")

        token = token.strip()

        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("El token de acceso está mal formado") from exc

        algorithm = header.get("alg")
        if algorithm != self._settings.algorithm:
            raise AuthenticationError("El token de acceso utiliza un algoritmo no permitido")

        kid = header.get("kid")
        if not isinstance(kid, str) or not kid.strip():
            raise AuthenticationError("El encabezado del token de acceso no contiene kid")

        signing_key = self._jwks_client.get_signing_key(kid)

        try:
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=[self._settings.algorithm],
                issuer=self._settings.issuer,
                audience=self._settings.audience,
                options={
                    "require": ["exp", "iss", "aud", "sub"],
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("El token de acceso ha expirado") from exc
        except jwt.InvalidIssuerError as exc:
            raise AuthenticationError("El issuer del token de acceso es inválido") from exc
        except jwt.InvalidAudienceError as exc:
            raise AuthenticationError("La audiencia del token de acceso es inválida") from exc
        except jwt.MissingRequiredClaimError as exc:
            raise AuthenticationError(
                f"Al token de acceso le falta el claim obligatorio: {exc.claim}"
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("El token de acceso es inválido") from exc

        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise AuthenticationError("El subject del token de acceso es inválido")

        issuer = payload.get("iss")
        if not isinstance(issuer, str):
            raise AuthenticationError("El issuer del token de acceso es inválido")

        audiences = _normalize_audiences(payload.get("aud"))
        roles = _extract_client_roles(payload, self._settings.audience)
        permissions = extract_permission_grants(roles)

        exp = payload.get("exp")
        try:
            expires_at = datetime.fromtimestamp(float(exp), tz=timezone.utc)
        except (TypeError, ValueError, OverflowError) as exc:
            raise AuthenticationError("La fecha de expiración del token de acceso es inválida") from exc

        username = payload.get("preferred_username")
        email = payload.get("email")

        return TokenClaims(
            subject=subject.strip(),
            issuer=issuer,
            audiences=audiences,
            expires_at=expires_at,
            roles=roles,
            permissions=permissions,
            preferred_username=username if isinstance(username, str) else None,
            email=email if isinstance(email, str) else None,
            raw=MappingProxyType(dict(payload)),
        )


def _normalize_audiences(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    raise AuthenticationError("La audiencia del token de acceso es inválida")


def _extract_client_roles(
    payload: Mapping[str, Any],
    audience: str,
) -> frozenset[str]:
    resource_access = payload.get("resource_access")
    if not isinstance(resource_access, dict):
        return frozenset()

    client_access = resource_access.get(audience)
    if not isinstance(client_access, dict):
        return frozenset()

    raw_roles = client_access.get("roles")
    if not isinstance(raw_roles, list):
        return frozenset()

    return frozenset(
        role.strip()
        for role in raw_roles
        if isinstance(role, str) and role.strip()
    )
