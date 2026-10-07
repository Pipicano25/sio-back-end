"""Adaptador HTTP de Party Identity (contrato 003 con la ampliación documental C-01).

`GET /organization-identities/{id}` con la identidad técnica de Purchase
(`perm:party-identity:organization_identities:read`). Lee `identification_type` e
`identification_number`, garantizados tras la ampliación aprobada (FR-047). `404` → `None`
(inexistente, `422`); identificación ausente o vacía → campos `None` (existe pero no apta, `409`;
D-08); indisponibilidad → `503`.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from purchase_service.application.exceptions import PARTY_IDENTITY
from purchase_service.application.ports import OrganizationInfo
from purchase_service.infrastructure.http_client import HTTPDependencyClient, TechnicalCaller, UnexpectedBody


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

    def get_organization(self, organization_id: UUID) -> OrganizationInfo | None:
        body = self._caller.get_object("organization_identity", f"/organization-identities/{organization_id}")
        if body is None:
            return None
        try:
            return OrganizationInfo(
                id=organization_id,
                identification_type=_optional_text(body, "identification_type"),
                identification_number=_optional_text(body, "identification_number"),
            )
        except UnexpectedBody as exc:
            raise self._caller.client.unavailable(
                "organization_identity", outcome=f"cuerpo_inesperado:{exc}"
            ) from None


def _optional_text(body: dict, name: str) -> str | None:
    value = body.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise UnexpectedBody(name)
    return value
