"""Adaptador HTTP de Party Identity (contrato 003 con las ampliaciones documentales de la 014 y la 015).

`GET /person-identities/{id}` y `GET /organization-identities/{id}` con la identidad técnica de
Sales (`perm:party-identity:{person,organization}_identities:read`). Lee `identification_type` e
`identification_number`, garantizados tras las ampliaciones aprobadas (C-01). `404` → `None`
(inexistente, `422`); identificación ausente o vacía → campos `None` (existe pero no apta, `409`);
indisponibilidad → `503`.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from sales_service.application.exceptions import PARTY_IDENTITY
from sales_service.application.ports import IdentityInfo
from sales_service.infrastructure.http_client import HTTPDependencyClient, TechnicalCaller, UnexpectedBody


class HTTPPartyDirectory:
    def __init__(
        self, *, base_url: str, timeout_seconds: float, tokens, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._caller = TechnicalCaller(
            HTTPDependencyClient(
                provider=PARTY_IDENTITY,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                unavailable_cause="party_identity_unreachable",
                transport=transport,
            ),
            tokens,
        )

    def _identity(self, operation: str, path: str, identity_id: UUID) -> IdentityInfo | None:
        body = self._caller.get_object(operation, path)
        if body is None:
            return None
        try:
            return IdentityInfo(
                id=identity_id,
                identification_type=_optional_text(body, "identification_type"),
                identification_number=_optional_text(body, "identification_number"),
            )
        except UnexpectedBody as exc:
            raise self._caller.client.unavailable(operation, outcome=f"cuerpo_inesperado:{exc}") from None

    def get_person(self, person_id: UUID) -> IdentityInfo | None:
        return self._identity("person_identity", f"/person-identities/{person_id}", person_id)

    def get_organization(self, organization_id: UUID) -> IdentityInfo | None:
        return self._identity(
            "organization_identity", f"/organization-identities/{organization_id}", organization_id
        )


def _optional_text(body: dict, name: str) -> str | None:
    value = body.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise UnexpectedBody(name)
    return value
