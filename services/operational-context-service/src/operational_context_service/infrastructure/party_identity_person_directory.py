"""Adaptador HTTP de personas contra Party Identity Service (R-08).

Única implementación productiva del puerto `PersonDirectory`. Para validar solo
lee `id` y `status`. El listado de empleados por sucursal lee además el nombre y
la identificación para mostrarlos, sin copiarlos (Principio III, FR-065).
Contrato: `specs/005-operational-context-users/contracts/party-identity-dependency.md`.
"""

from uuid import UUID

import httpx

from operational_context_service.application.exceptions import (
    PARTY_IDENTITY_UNAVAILABLE,
    PERSON_VALIDATION_DENIED,
)
from operational_context_service.application.ports import ExternalRef, PersonProfile
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

    def get_person_profile(self, person_identity_id: UUID) -> PersonProfile | None:
        """Nombre e identificación para el listado de empleados por sucursal; no se persisten."""
        operation = "get_person_profile"
        body = self._client.get_json(operation, f"/person-identities/{person_identity_id}")

        if body is None:
            return None

        status = body.get("status")

        if status not in VALID_STATUSES:
            raise self._client.unexpected_body(operation)

        return PersonProfile(
            id=person_identity_id,
            status=status,
            identification_type=_text(body.get("identification_type")),
            identification_number=_text(body.get("identification_number")),
            first_name=_text(body.get("first_name")),
            middle_name=_text(body.get("middle_name")),
            last_name=_text(body.get("last_name")),
            second_last_name=_text(body.get("second_last_name")),
        )


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None
