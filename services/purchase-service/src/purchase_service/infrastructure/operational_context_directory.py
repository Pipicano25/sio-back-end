"""Adaptadores HTTP de Operational Context (`contracts/dependencies.md`; R-02, R-06).

- `HTTPOperationalContextDirectory`: empresa, sucursal y usuario operativo por UUID con la
  **identidad técnica de Purchase** (`*:read` + `platform:lookup`).
- `HTTPAccessDirectory`: `operational-access` con **el token del usuario** (vía propia;
  nunca el técnico), por sucursal (escrituras) o por empresa (lecturas y secuencias).

`5xx`, `401` tras renovar, `403` en llamadas técnicas, red, tiempo agotado o cuerpo
inesperado → `DependencyUnavailableError("operational-context")`.
"""

from __future__ import annotations

import re
from uuid import UUID

import httpx

from purchase_service.application.exceptions import OPERATIONAL_CONTEXT, OperationalAccessDeniedError
from purchase_service.application.ports import AccessResult, ApplicationUserInfo, BranchInfo, CompanyInfo
from purchase_service.infrastructure.http_client import (
    HTTPDependencyClient,
    TechnicalCaller,
    UnexpectedBody,
    json_object,
    logger,
    text_field,
    uuid_field,
)

_CURRENCY = re.compile(r"^[A-Z]{3}$")
UNREACHABLE = "operational_context_unreachable"


def _client(base_url: str, timeout_seconds: float, transport: httpx.BaseTransport | None) -> HTTPDependencyClient:
    return HTTPDependencyClient(
        provider=OPERATIONAL_CONTEXT,
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        unavailable_cause=UNREACHABLE,
        transport=transport,
    )


class HTTPOperationalContextDirectory:
    """Empresa, sucursal y usuario operativo con la identidad técnica de Purchase."""

    def __init__(
        self, *, base_url: str, timeout_seconds: float, tokens, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._caller = TechnicalCaller(_client(base_url, timeout_seconds, transport), tokens)

    def get_company(self, company_id: UUID) -> CompanyInfo | None:
        body = self._caller.get_object("company", f"/companies/{company_id}")
        if body is None:
            return None
        try:
            currency = text_field(body, "default_currency")
            if not _CURRENCY.match(currency or ""):
                raise UnexpectedBody("default_currency")
            return CompanyInfo(id=company_id, status=text_field(body, "status"), default_currency=currency)
        except UnexpectedBody as exc:
            raise self._caller.client.unavailable("company", outcome=f"cuerpo_inesperado:{exc}") from None

    def get_branch(self, branch_id: UUID) -> BranchInfo | None:
        body = self._caller.get_object("branch", f"/branches/{branch_id}")
        if body is None:
            return None
        try:
            return BranchInfo(
                id=branch_id,
                company_id=uuid_field(body, "company_id"),
                status=text_field(body, "status"),
                effective_timezone=text_field(body, "effective_timezone"),
            )
        except UnexpectedBody as exc:
            raise self._caller.client.unavailable("branch", outcome=f"cuerpo_inesperado:{exc}") from None

    def get_application_user(self, application_user_id: UUID) -> ApplicationUserInfo | None:
        body = self._caller.get_object("application_user", f"/application-users/{application_user_id}")
        if body is None:
            return None
        try:
            return ApplicationUserInfo(
                id=application_user_id, company_id=uuid_field(body, "company_id"), status=text_field(body, "status")
            )
        except UnexpectedBody as exc:
            raise self._caller.client.unavailable("application_user", outcome=f"cuerpo_inesperado:{exc}") from None


class HTTPAccessDirectory:
    """`operational-access` con el token del usuario (R-02)."""

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

    def _access(self, params: dict[str, str]) -> AccessResult:
        operation = "operational_access"
        response = self._client.send(
            operation, "GET", "/operational-access", authorization=self._authorization, params=params
        )

        if response.status_code == 403:
            logger.warning("Operational Context negó la evaluación de acceso al usuario operacion=%s", operation)
            raise OperationalAccessDeniedError()

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)

        if body is None or not isinstance(body.get("allowed"), bool):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        reason = body.get("reason")

        try:
            company_id = uuid_field(body, "company_id", optional=True)
            user_id = uuid_field(body, "application_user_id", optional=True)
        except UnexpectedBody:
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado") from None

        if reason is not None and not isinstance(reason, str):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        return AccessResult(body["allowed"], reason, company_id, user_id)

    def check_branch(self, branch_id: UUID) -> AccessResult:
        return self._access({"branch_id": str(branch_id)})

    def check_company(self, company_id: UUID) -> AccessResult:
        return self._access({"company_id": str(company_id)})
