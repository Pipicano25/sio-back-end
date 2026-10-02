"""Adaptador de membresía contra Operational Context (R-06, DS-01, C-07).

Única implementación productiva del puerto `MembershipResolver`, usada en todos
los entornos. Reutiliza la **vía técnica** del contrato Provider existente
`GET /operational-access` (`specs/005-operational-context-users/contracts/
operational-access-provider.md`): token `client_credentials` propio del servicio,
`company_id` y el `sub` del usuario como `keycloak_user_id`, sin `permission`
(Operational Context no necesita leer Keycloak). El token del usuario nunca se
propaga a Operational Context.

Renovación técnica: ante el **primer** `401` se invalida el token, se obtiene uno
nuevo y se repite la llamada exactamente una vez. Tiempo agotado, red, `5xx` y
`403` no se reintentan (FR-028). Solo se leen `allowed`, `reason` y
`application_user_id` (Principio III).
"""

from __future__ import annotations

import logging
from typing import Any, Protocol
from uuid import UUID

import httpx

from party_identity_service.application.exceptions import (
    KEYCLOAK_TOKEN_UNAVAILABLE,
    OPERATIONAL_CONTEXT_UNAVAILABLE,
    OPERATIONAL_CONTEXT_VALIDATION_DENIED,
    CompanyInactiveError,
    CompanyNotFoundError,
    ConfirmationMembershipInvalidError,
    DependencyUnavailableError,
)
from party_identity_service.infrastructure.keycloak_token_client import TokenRequestError
from party_identity_service.observability import (
    SERVICE_LOGGER,
    build_traceparent,
    current_trace_id,
)

logger = logging.getLogger(SERVICE_LOGGER)

MEMBERSHIP_REASONS = {"USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE"}


class TechnicalToken(Protocol):
    """Token técnico en caché (ver `CachedClientCredentialsToken`)."""

    def get(self) -> str: ...

    def invalidate(self) -> None: ...


class HTTPOperationalContextMembershipResolver:
    """Resuelve el `ApplicationUser` del usuario en la empresa de confirmación."""

    def __init__(
        self,
        *,
        base_url: str,
        tokens: TechnicalToken,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.tokens = tokens
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def resolve(self, *, company_id: UUID, keycloak_user_id: str) -> UUID:
        params = {"company_id": str(company_id), "keycloak_user_id": keycloak_user_id}

        response = self._call(params)
        if response.status_code == 401:
            # Renovación técnica de la credencial: una sola repetición.
            self.tokens.invalidate()
            response = self._call(params)
            if response.status_code == 401:
                raise self._denied(401)

        if response.status_code == 403:
            raise self._denied(403)
        if response.status_code == 404:
            raise CompanyNotFoundError
        if response.status_code != 200:
            raise self._unavailable(f"estado {response.status_code}")

        body = self._json(response)
        allowed = body.get("allowed")
        reason = body.get("reason")

        if allowed is True:
            try:
                return UUID(str(body["application_user_id"]))
            except (KeyError, ValueError, TypeError):
                raise self._unavailable("application_user_id ausente o inválido") from None

        if allowed is False and reason == "COMPANY_INACTIVE":
            raise CompanyInactiveError
        if allowed is False and reason in MEMBERSHIP_REASONS:
            raise ConfirmationMembershipInvalidError(reason=reason)

        raise self._unavailable("allowed/reason inesperados")

    # -- interno --------------------------------------------------------------

    def _call(self, params: dict[str, str]) -> httpx.Response:
        try:
            token = self.tokens.get()
        except TokenRequestError as exc:
            logger.error(
                "No fue posible obtener el token técnico causa=%s detalle=%s",
                KEYCLOAK_TOKEN_UNAVAILABLE,
                exc,
            )
            raise DependencyUnavailableError(
                dependency="keycloak",
                cause=KEYCLOAK_TOKEN_UNAVAILABLE,
            ) from None

        headers = {"Authorization": f"Bearer {token}"}
        trace_id = current_trace_id()
        if trace_id:
            headers["traceparent"] = build_traceparent(trace_id)

        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                return client.get(f"{self.base_url}/operational-access", params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise self._unavailable(type(exc).__name__) from None

    def _json(self, response: httpx.Response) -> dict[str, Any]:
        try:
            body = response.json()
        except ValueError:
            raise self._unavailable("cuerpo no JSON") from None
        if not isinstance(body, dict):
            raise self._unavailable("cuerpo inesperado")
        return body

    @staticmethod
    def _denied(status: int) -> DependencyUnavailableError:
        logger.warning(
            "Operational Context rechazó la consulta técnica causa=%s estado=%s",
            OPERATIONAL_CONTEXT_VALIDATION_DENIED,
            status,
        )
        return DependencyUnavailableError(
            dependency="operational-context",
            cause=OPERATIONAL_CONTEXT_VALIDATION_DENIED,
        )

    @staticmethod
    def _unavailable(outcome: str) -> DependencyUnavailableError:
        logger.error(
            "Operational Context no disponible causa=%s resultado=%s",
            OPERATIONAL_CONTEXT_UNAVAILABLE,
            outcome,
        )
        return DependencyUnavailableError(
            dependency="operational-context",
            cause=OPERATIONAL_CONTEXT_UNAVAILABLE,
        )
