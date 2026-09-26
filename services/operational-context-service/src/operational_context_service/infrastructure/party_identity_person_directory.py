"""Adaptador HTTP de personas contra Party Identity Service (R-08).

Única implementación productiva del puerto `PersonDirectory`. Solo lee `id` y
`status`; no copia nombres ni identificación (Principio III, FR-065).
Contrato: `specs/005-operational-context-users/contracts/party-identity-dependency.md`.
"""

from uuid import UUID

import httpx

from operational_context_service.application.exceptions import (
    PARTY_IDENTITY_UNAVAILABLE,
    PERSON_VALIDATION_DENIED,
)
from operational_context_service.application.ports import ExternalRef
from operational_context_service.infrastructure.http_lookup import HTTPLookupClient

PROVIDER = "party-identity"
VALID_STATUSES = {"ACTIVE", "INACTIVE"}


class HTTPPartyIdentityPersonDirectory:
    """Consulta `GET {base}/person-identities/{id}` propagando el token del usuario (D5)."""

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
            denied_cause=PERSON_VALIDATION_DENIED,
            unavailable_cause=PARTY_IDENTITY_UNAVAILABLE,
            transport=transport,
        )

    def get_person(self, person_identity_id: UUID) -> ExternalRef | None:
        operation = "get_person"
        body = self._client.get_json(operation, f"/person-identities/{person_identity_id}")

        if body is None:
            return None

        status = body.get("status")

        if status not in VALID_STATUSES:
            raise self._client.unexpected_body(operation)

        return ExternalRef(id=person_identity_id, status=status)
