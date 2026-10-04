"""Adaptador HTTP de Party Identity (`contracts/party-identity-dependency.md`).

Propaga el token del usuario (DS-04). `403` es una denegación al usuario
(`PARTY_IDENTITY_ACCESS_DENIED`), nunca indisponibilidad; `401`, `5xx`, red y
tiempo agotado son indisponibilidad (FR-054, FR-055). Solo se leen `status`,
`organization_identity_id` e `is_active`; nada se persiste salvo el UUID. En el
resumen de empresas (FR-046) se lee además `legal_name` solo para mostrarlo: ahí
`404` y `403` dan `None`.
"""

from __future__ import annotations

import logging
from uuid import UUID

import httpx

from commercial_relationship_service.application.exceptions import (
    PARTY_IDENTITY,
    PARTY_IDENTITY_FORBIDDEN,
    PARTY_IDENTITY_UNREACHABLE,
    PartyIdentityAccessDeniedError,
)
from commercial_relationship_service.application.ports import ContactPersonRef, IdentityRef
from commercial_relationship_service.infrastructure.http_lookup import (
    HTTPDependencyClient,
    json_object,
    logger,
)


class HTTPPartyDirectory:
    """Personas, organizaciones y personas de contacto por UUID."""

    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = HTTPDependencyClient(
            provider=PARTY_IDENTITY,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            unavailable_cause=PARTY_IDENTITY_UNREACHABLE,
            transport=transport,
        )
        self._authorization = authorization

    def get_person(self, person_identity_id: UUID) -> IdentityRef | None:
        return self._identity("get_person", f"/person-identities/{person_identity_id}", person_identity_id)

    def get_organization(self, organization_identity_id: UUID) -> IdentityRef | None:
        return self._identity(
            "get_organization",
            f"/organization-identities/{organization_identity_id}",
            organization_identity_id,
        )

    def get_contact_person(self, contact_person_id: UUID) -> ContactPersonRef | None:
        operation = "get_contact_person"
        body = self._get(operation, f"/organization-contact-persons/{contact_person_id}")

        if body is None:
            return None

        try:
            return ContactPersonRef(
                id=contact_person_id,
                organization_identity_id=UUID(str(body["organization_identity_id"])),
                is_active=_as_bool(body["is_active"]),
            )
        except (KeyError, ValueError, TypeError):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado") from None

    def find_organization_name(self, organization_identity_id: UUID) -> str | None:
        operation = "get_organization_name"
        response = self._client.send(
            operation,
            "GET",
            f"/organization-identities/{organization_identity_id}",
            authorization=self._authorization,
        )

        if response.status_code in {403, 404}:
            return None

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)
        name = None if body is None else body.get("legal_name")

        if not isinstance(name, str):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        return name

    def _identity(self, operation: str, path: str, identity_id: UUID) -> IdentityRef | None:
        body = self._get(operation, path)

        if body is None:
            return None

        status = body.get("status")

        if status not in {"ACTIVE", "INACTIVE"}:
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        return IdentityRef(id=identity_id, status=status)

    def _get(self, operation: str, path: str) -> dict | None:
        response = self._client.send(operation, "GET", path, authorization=self._authorization)

        if response.status_code == 404:
            return None

        if response.status_code == 403:
            logger.log(
                logging.WARNING,
                "Party Identity negó la consulta al usuario causa=%s operacion=%s",
                PARTY_IDENTITY_FORBIDDEN,
                operation,
            )
            raise PartyIdentityAccessDeniedError()

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)

        if body is None:
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        return body


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    raise TypeError("is_active no es booleano")
