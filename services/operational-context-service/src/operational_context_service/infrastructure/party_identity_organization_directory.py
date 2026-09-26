"""Adaptador HTTP de organizaciones contra Party Identity Service.

Única implementación productiva del puerto `OrganizationDirectory`, usada en
todos los entornos (R-12). Solo lee `id` y `status`; no copia la razón social,
el nombre comercial ni la identificación (Principio III, DS-01, DS-13).
Contrato: `contracts/party-identity-dependency.md`.
"""

from uuid import UUID

import httpx

from operational_context_service.application.exceptions import (
    ORGANIZATION_VALIDATION_DENIED,
    PARTY_IDENTITY_UNAVAILABLE,
)
from operational_context_service.application.ports import ExternalRef
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
