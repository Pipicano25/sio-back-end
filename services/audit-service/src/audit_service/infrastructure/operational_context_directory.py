"""Adaptador HTTP de Operational Context (`contracts/operational-context-dependency.md`).

`GET {base}/operational-access?company_id=` por la vía propia, propagando
**siempre** el `Authorization` del usuario que consulta (FR-050): Audit no tiene
identidad técnica propia y nunca sustituye la del usuario. Operational Context
exige además al usuario `perm:operational-context:application_users:read`
(FR-037); si responde `403`, Audit responde `403 OPERATIONAL_ACCESS_DENIED`.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from audit_service.application.exceptions import OperationalAccessDeniedError
from audit_service.application.ports import CompanyAccess
from audit_service.infrastructure.http_lookup import HTTPDependencyClient, json_object, logger

OPERATIONAL_CONTEXT = "operational-context"
_NOT_MEMBER = {"USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE"}


class HTTPCompanyAccessDirectory:
    """Membresía del usuario en una empresa, con su propio token."""

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
            logger.warning(
                "Operational Context negó la evaluación de acceso al usuario operacion=%s", operation
            )
            raise OperationalAccessDeniedError(
                "No tiene permiso para consultar el acceso operativo requerido. Solicite acceso "
                "al administrador del sistema indicando el trace_id."
            )

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)

        if body is None or not isinstance(body.get("allowed"), bool):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        if body["allowed"]:
            return CompanyAccess(member_active=True)

        reason = body.get("reason")

        if reason in _NOT_MEMBER:
            return CompanyAccess(member_active=False)

        if reason == "COMPANY_INACTIVE":
            # La auditoría se consulta aunque la empresa esté inactiva (R-09).
            return CompanyAccess(member_active=True)

        raise self._client.unavailable(operation, outcome=f"causa_inesperada={reason}")
