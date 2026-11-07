"""Adaptador HTTP de Party Identity (contrato 003 con las ampliaciones documentales de la 014 y la 015).

`GET /person-identities/{id}` y `GET /organization-identities/{id}` con la identidad técnica de
Sales (`perm:party-identity:{person,organization}_identities:read`). Lee `identification_type` e
`identification_number`, garantizados tras las ampliaciones aprobadas (C-01). `404` → `None`
(inexistente, `422`); identificación ausente o vacía → campos `None` (existe pero no apta, `409`);
indisponibilidad → `503`.

También lee el nombre y el estado, y lista una página de identidades `ACTIVE` (`GET /person-identities` y
`GET /organization-identities`) para el listado de clientes de la venta.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from sales_service.application.exceptions import PARTY_IDENTITY
from sales_service.application.ports import ORGANIZATION, IdentityInfo, IdentityPage
from sales_service.infrastructure.http_client import (
    HTTPDependencyClient,
    TechnicalCaller,
    UnexpectedBody,
    int_field,
    json_object,
    uuid_field,
)

PATHS = {ORGANIZATION: "/organization-identities"}
PERSON_PATH = "/person-identities"


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
            return _info(body, identity_id)
        except UnexpectedBody as exc:
            raise self._caller.client.unavailable(operation, outcome=f"cuerpo_inesperado:{exc}") from None

    def search(self, customer_kind: str, search: str | None, page: int, page_size: int) -> IdentityPage:
        operation = "identities_search"
        params = {"status": "ACTIVE", "page": str(page), "page_size": str(page_size)}
        if search:
            params["search"] = search
        response = self._caller.send(operation, "GET", PATHS.get(customer_kind, PERSON_PATH), params=params)
        if response.status_code != 200:
            raise self._caller.client.unavailable(operation, outcome=f"estado={response.status_code}")
        body = json_object(response)
        items = body.get("items") if body else None
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise self._caller.client.unavailable(operation, outcome="cuerpo_inesperado")
        try:
            return IdentityPage(
                items=[_info(item, uuid_field(item, "id")) for item in items],
                total_records=int_field(body, "total_records"),
            )
        except UnexpectedBody as exc:
            raise self._caller.client.unavailable(operation, outcome=f"cuerpo_inesperado:{exc}") from None

    def get_person(self, person_id: UUID) -> IdentityInfo | None:
        return self._identity("person_identity", f"/person-identities/{person_id}", person_id)

    def get_organization(self, organization_id: UUID) -> IdentityInfo | None:
        return self._identity(
            "organization_identity", f"/organization-identities/{organization_id}", organization_id
        )


def _info(body: dict, identity_id: UUID) -> IdentityInfo:
    return IdentityInfo(
        id=identity_id,
        identification_type=_optional_text(body, "identification_type"),
        identification_number=_optional_text(body, "identification_number"),
        name=_name(body),
        status=_optional_text(body, "status"),
    )


def _name(body: dict) -> str | None:
    """Organización: nombre comercial o razón social; persona: nombres y apellidos."""
    if "legal_name" in body:
        return _optional_text(body, "trade_name") or _optional_text(body, "legal_name")
    parts = [_optional_text(body, key) for key in ("first_name", "middle_name", "last_name", "second_last_name")]
    return " ".join(part.strip() for part in parts if part) or None


def _optional_text(body: dict, name: str) -> str | None:
    value = body.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if not isinstance(value, str):
        raise UnexpectedBody(name)
    return value
