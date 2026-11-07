"""Clientes de la empresa en Commercial Relationship con **el token del usuario** (registro automático).

Se usa el token del vendedor, no el técnico: Commercial Relationship exige la membresía `ACTIVE` del usuario en
la empresa para listar y registrar clientes, y la auditoría del alta queda a su nombre
(`perm:commercial-relationship:company_customers:read` y `:create`).

`GET /companies/{c}/company-customers` con `status=ALL` y la identidad repetida (una sola llamada por página);
`POST /companies/{c}/company-customers` para el alta. `403`, `404`, `409` y `422` del alta →
`CustomerRejection` con el `code` sin prefijo y el `detail`; cualquier otro estado → `503 commercial-relationship`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import httpx

from sales_service.application.exceptions import COMMERCIAL_RELATIONSHIP
from sales_service.application.ports import PERSON, CustomerInfo, CustomerRejection
from sales_service.infrastructure.http_client import (
    HTTPDependencyClient,
    UnexpectedBody,
    json_object,
    text_field,
    uuid_field,
)

CODE_PREFIX = "COMMERCIAL_RELATIONSHIP."
REJECTIONS = frozenset({403, 404, 409, 422})


def _identity_field(customer_kind: str) -> str:
    return "person_identity_id" if customer_kind == PERSON else "organization_identity_id"


def _customer(body: dict[str, Any]) -> CustomerInfo:
    return CustomerInfo(
        id=uuid_field(body, "id"),
        company_id=uuid_field(body, "company_id"),
        customer_kind=text_field(body, "customer_kind"),
        person_identity_id=uuid_field(body, "person_identity_id", optional=True),
        organization_identity_id=uuid_field(body, "organization_identity_id", optional=True),
        display_name=text_field(body, "display_name"),
        status=text_field(body, "status"),
    )


class HTTPCustomerRegistry:
    def __init__(
        self,
        *,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = HTTPDependencyClient(
            provider=COMMERCIAL_RELATIONSHIP,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            unavailable_cause="commercial_relationship_unreachable",
            transport=transport,
        )
        self._authorization = authorization

    def find(self, company_id: UUID, customer_kind: str, identity_ids: Sequence[UUID]) -> dict[UUID, CustomerInfo]:
        operation = "company_customers_by_identity"
        distinct = list(dict.fromkeys(identity_ids))
        if not distinct:
            return {}
        field = _identity_field(customer_kind)
        response = self._client.send(
            operation,
            "GET",
            f"/companies/{company_id}/company-customers",
            authorization=self._authorization,
            params={
                "status": "ALL",
                "customer_kind": customer_kind,
                field: [str(value) for value in distinct],
                "page_size": "100",
            },
        )
        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")
        body = json_object(response)
        items = body.get("items") if body else None
        if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")
        try:
            customers = [_customer(item) for item in items]
        except UnexpectedBody as exc:
            raise self._client.unavailable(operation, outcome=f"cuerpo_inesperado:{exc}") from None
        result: dict[UUID, CustomerInfo] = {}
        for customer in customers:
            identity_id = customer.person_identity_id if customer_kind == PERSON else customer.organization_identity_id
            if customer.company_id == company_id and identity_id is not None:
                result[identity_id] = customer
        return result

    def create(
        self, company_id: UUID, customer_kind: str, identity_id: UUID, internal_code: str, display_name: str
    ) -> CustomerInfo:
        operation = "company_customer_create"
        response = self._client.send(
            operation,
            "POST",
            f"/companies/{company_id}/company-customers",
            authorization=self._authorization,
            json={
                "customer_kind": customer_kind,
                _identity_field(customer_kind): str(identity_id),
                "internal_code": internal_code,
                "display_name": display_name,
            },
        )
        body = json_object(response)
        if response.status_code in REJECTIONS:
            code = body.get("code") if body else None
            detail = body.get("detail") if body else None
            raise CustomerRejection(
                response.status_code,
                code.removeprefix(CODE_PREFIX) if isinstance(code, str) else None,
                detail if isinstance(detail, str) else None,
            )
        if response.status_code != 201 or body is None:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")
        try:
            return _customer(body)
        except UnexpectedBody as exc:
            raise self._client.unavailable(operation, outcome=f"cuerpo_inesperado:{exc}") from None
