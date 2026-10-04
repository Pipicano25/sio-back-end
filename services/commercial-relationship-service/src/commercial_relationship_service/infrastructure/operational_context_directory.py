"""Adaptadores HTTP de Operational Context (`contracts/operational-context-dependency.md`).

Usan siempre el token del usuario (D5, DS-04): la vía propia de
`operational-access` (R-02), la empresa por UUID para la autorreferencia (R-07) y,
en el resumen de empresas (FR-046), `me/operational-context` y la empresa por UUID
para mostrar su razón social.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from commercial_relationship_service.application.exceptions import (
    OPERATIONAL_ACCESS_FORBIDDEN,
    OPERATIONAL_CONTEXT,
    OPERATIONAL_CONTEXT_UNREACHABLE,
    NotFoundError,
    OperationalAccessDeniedError,
)
from commercial_relationship_service.application.ports import CompanyAccess, MemberCompany
from commercial_relationship_service.infrastructure.http_lookup import (
    HTTPDependencyClient,
    json_object,
    logger,
)

_NOT_MEMBER = {"USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE"}
_STATUSES = {"ACTIVE", "INACTIVE"}


def _client(base_url: str, timeout_seconds: float, transport: httpx.BaseTransport | None):
    return HTTPDependencyClient(
        provider=OPERATIONAL_CONTEXT,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        unavailable_cause=OPERATIONAL_CONTEXT_UNREACHABLE,
        transport=transport,
    )


def _forbidden(operation: str) -> OperationalAccessDeniedError:
    logger.warning(
        "Operational Context negó la consulta al usuario causa=%s operacion=%s",
        OPERATIONAL_ACCESS_FORBIDDEN,
        operation,
    )
    return OperationalAccessDeniedError()


class HTTPCompanyAccessDirectory:
    """`GET {base}/operational-access?company_id=` por la vía propia (sin `permission`)."""

    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = _client(base_url, timeout_seconds, transport)
        self._authorization = authorization

    def check_company_access(self, company_id: UUID) -> CompanyAccess:
        operation = "operational_access"
        response = self._client.send(
            operation,
            "GET",
            "/operational-access",
            authorization=self._authorization,
            params={"company_id": str(company_id)},
        )

        if response.status_code == 403:
            raise _forbidden(operation)

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)

        if body is None or not isinstance(body.get("allowed"), bool):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        if body["allowed"]:
            return CompanyAccess(member_active=True, company_active=True)

        reason = body.get("reason")

        if reason in _NOT_MEMBER:
            return CompanyAccess(member_active=False, company_active=None)

        if reason == "COMPANY_INACTIVE":
            return CompanyAccess(member_active=True, company_active=False)

        # Sin sucursal ni permiso no caben otras causas: respuesta fuera del contrato.
        raise self._client.unavailable(operation, outcome=f"causa_inesperada={reason}")

    def list_member_companies(self) -> list[MemberCompany]:
        operation = "me_operational_context"
        response = self._client.send(
            operation, "GET", "/me/operational-context", authorization=self._authorization
        )

        if response.status_code == 403:
            raise _forbidden(operation)

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)
        memberships = None if body is None else body.get("memberships")

        if not isinstance(memberships, list):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        companies: dict[UUID, MemberCompany] = {}

        try:
            for membership in memberships:
                if membership["status"] not in _STATUSES or membership["company_status"] not in _STATUSES:
                    raise ValueError("estado fuera de contrato")
                if membership["status"] == "ACTIVE":
                    company_id = UUID(str(membership["company_id"]))
                    companies[company_id] = MemberCompany(
                        company_id=company_id, company_status=membership["company_status"]
                    )
        except (KeyError, TypeError, ValueError):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado") from None

        return sorted(companies.values(), key=lambda company: str(company.company_id))


class HTTPCompanyDirectory:
    """`GET {base}/companies/{id}`: solo se lee `organization_identity_id` (FR-028)."""

    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = _client(base_url, timeout_seconds, transport)
        self._authorization = authorization

    def get_company_organization(self, company_id: UUID) -> UUID:
        operation = "get_company"
        response = self._client.send(
            operation, "GET", f"/companies/{company_id}", authorization=self._authorization
        )

        if response.status_code == 404:
            raise NotFoundError

        if response.status_code == 403:
            raise _forbidden(operation)

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        return self._organization_of(operation, response)

    def find_company_organization(self, company_id: UUID) -> UUID | None:
        operation = "get_company_for_summary"
        response = self._client.send(
            operation, "GET", f"/companies/{company_id}", authorization=self._authorization
        )

        if response.status_code in {403, 404}:
            return None

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        return self._organization_of(operation, response)

    def _organization_of(self, operation: str, response: httpx.Response) -> UUID:
        body = json_object(response) or {}

        try:
            return UUID(str(body["organization_identity_id"]))
        except (KeyError, ValueError):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado") from None
