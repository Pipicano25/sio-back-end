"""Adaptador HTTP de organizaciones contra Party Identity Service.

Única implementación productiva del puerto `OrganizationDirectory`, usada en
todos los entornos (R-12). Para validar solo lee `id` y `status`. El contexto
operativo propio lee además la razón social, el nombre comercial y la
identificación para mostrarlos, sin copiarlos (Principio III, DS-01, DS-13).
Contrato: `contracts/party-identity-dependency.md`.
"""

from uuid import UUID

import httpx

from operational_context_service.application.exceptions import (
    ORGANIZATION_VALIDATION_DENIED,
    PARTY_IDENTITY_UNAVAILABLE,
)
from operational_context_service.application.ports import ExternalRef, OrganizationProfile
from operational_context_service.infrastructure.http_lookup import HTTPLookupClient

PROVIDER = "party-identity"
VALID_STATUSES = {"ACTIVE", "INACTIVE"}


class HTTPPartyIdentityOrganizationDirectory:
    """Consulta `GET {base}/organization-identities/{id}` propagando el token del usuario."""

    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = HTTPLookupClient(
            provider=PROVIDER,
            base_url=base_url,
            authorization=authorization,
            timeout_seconds=timeout_seconds,
            denied_cause=ORGANIZATION_VALIDATION_DENIED,
            unavailable_cause=PARTY_IDENTITY_UNAVAILABLE,
            transport=transport,
        )

    def get_organization(self, organization_identity_id: UUID) -> ExternalRef | None:
        operation = "get_organization"
        body = self._client.get_json(
            operation,
            f"/organization-identities/{organization_identity_id}",
        )

        if body is None:
            return None

        status = body.get("status")

        if status not in VALID_STATUSES:
            raise self._client.unexpected_body(operation)

        return ExternalRef(id=organization_identity_id, status=status)

    def get_organization_profile(self, organization_identity_id: UUID) -> OrganizationProfile | None:
        """Nombre e identificación para mostrarlos en `/me/operational-context`; no se persisten."""
        operation = "get_organization_profile"
        body = self._client.get_json(
            operation,
            f"/organization-identities/{organization_identity_id}",
        )

        if body is None:
            return None

        status = body.get("status")

        if status not in VALID_STATUSES:
            raise self._client.unexpected_body(operation)

        return OrganizationProfile(
            id=organization_identity_id,
            status=status,
            legal_name=_text(body.get("legal_name")),
            trade_name=_text(body.get("trade_name")),
            identification_type=_text(body.get("identification_type")),
            identification_number=_text(body.get("identification_number")),
        )


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None
