"""Adaptadores HTTP de Operational Context (`contracts/dependencies.md`, R-07, R-08).

- `HTTPOperationalContextDirectory`: sucursal y usuario operativo por UUID con la
  **identidad técnica de Inventory** (`branches:read` / `application_users:read`
  + `platform:lookup`). El token se renueva una vez ante `401`.
- `HTTPCompanyAccessDirectory`: membresía del usuario consultante con **su propio
  token** (`operational-access?company_id=`, vía propia); nunca el técnico (FR-060).

`5xx`, `401` tras renovar, `403` en llamadas técnicas, red, tiempo agotado o cuerpo
inesperado → `DependencyUnavailableError("operational-context")`.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from inventory_service.application.exceptions import OPERATIONAL_CONTEXT, OperationalAccessDeniedError
from inventory_service.application.ports import ApplicationUserInfo, BranchInfo, TokenProvider
from inventory_service.infrastructure.http_lookup import HTTPDependencyClient, json_object, logger
from inventory_service.infrastructure.keycloak_token_client import (
    TokenUnavailableError,
    technical_dependency_error,
)

_ALLOWED_REASONS_FOR_READS = {"COMPANY_INACTIVE"}
_NOT_MEMBER = {"USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE"}


class TechnicalCaller:
    """Llamada con token técnico y una renovación ante `401`."""

    def __init__(self, client: HTTPDependencyClient, tokens: TokenProvider) -> None:
        self._client = client
        self._tokens = tokens

    def send(self, operation: str, method: str, path: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(2):
            try:
                token = self._tokens.get_token()
            except TokenUnavailableError:
                raise technical_dependency_error(self._client.provider, operation) from None

            response = self._client.send(operation, method, path, authorization=f"Bearer {token}", **kwargs)

            if response.status_code == 401 and attempt == 0:
                self._tokens.invalidate()
                continue

            return response

        return response


def _uuid(value: Any) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


class HTTPOperationalContextDirectory:
    """Sucursal y usuario operativo con la identidad técnica de Inventory."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        tokens: TokenProvider,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = HTTPDependencyClient(
            provider=OPERATIONAL_CONTEXT,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            unavailable_cause="operational_context_unreachable",
            transport=transport,
        )
        self._caller = TechnicalCaller(self._client, tokens)

    def _get(self, operation: str, path: str) -> dict[str, Any] | None:
        response = self._caller.send(operation, "GET", path)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)

        if body is None:
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        return body

    def get_branch(self, branch_id: UUID) -> BranchInfo | None:
        body = self._get("branch", f"/branches/{branch_id}")

        if body is None:
            return None

        company_id = _uuid(body.get("company_id"))
        status = body.get("status")
        company_status = body.get("company_status")

        if company_id is None or not isinstance(status, str) or not isinstance(company_status, str):
            raise self._client.unavailable("branch", outcome="cuerpo_inesperado")

        return BranchInfo(id=branch_id, company_id=company_id, status=status, company_status=company_status)

    def get_application_user(self, application_user_id: UUID) -> ApplicationUserInfo | None:
        body = self._get("application_user", f"/application-users/{application_user_id}")

        if body is None:
            return None

        company_id = _uuid(body.get("company_id"))
        status = body.get("status")

        if company_id is None or not isinstance(status, str):
            raise self._client.unavailable("application_user", outcome="cuerpo_inesperado")

        return ApplicationUserInfo(
            id=application_user_id,
            company_id=company_id,
            status=status,
            keycloak_user_id=_uuid(body.get("keycloak_user_id")),
        )


class HTTPCompanyAccessDirectory:
    """Membresía del usuario en una empresa, con su propio token (R-08)."""

    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = HTTPDependencyClient(
            provider=OPERATIONAL_CONTEXT,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            unavailable_cause="operational_context_unreachable",
            transport=transport,
        )
        self._authorization = authorization

    def is_member(self, company_id: UUID) -> bool:
        operation = "operational_access"
        response = self._client.send(
            operation,
            "GET",
            "/operational-access",
            authorization=self._authorization,
            params={"company_id": str(company_id)},
        )

        if response.status_code == 403:
            logger.warning("Operational Context negó la evaluación de acceso al usuario operacion=%s", operation)
            raise OperationalAccessDeniedError()

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)

        if body is None or not isinstance(body.get("allowed"), bool):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        if body["allowed"]:
            return True

        reason = body.get("reason")

        if reason in _NOT_MEMBER:
            return False

        if reason in _ALLOWED_REASONS_FOR_READS:
            # Saldo y kardex se consultan aunque la empresa esté inactiva (R-08).
            return True

        raise self._client.unavailable(operation, outcome=f"causa_inesperada={reason}")
