"""Adaptador HTTP de Inventory (contrato 012 + delta 013; research.md R-07).

- Entrada: `POST /inventory-entries` (`perm:inventory:entries:create`).
- Reverso: `POST /inventory-entries/{operation_id}/reversal`.
- Conciliación: `GET /companies/{c}/inventory-operations/by-key/{key}` (`movements:read` +
  `platform:lookup`).

`201`/`200` → referencia de la operación (solo su `id`, FR-046); `404`, `409` o `422` →
`InventoryRejection` (definitivo para ese contenido); `5xx`, `408`, `401` tras renovar,
`403`, red, tiempo agotado o cuerpo inesperado → `503 inventory` (se reintenta con la
misma clave y la misma solicitud).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from purchase_service.application.exceptions import INVENTORY
from purchase_service.application.ports import InventoryOperationRef, InventoryRejection
from purchase_service.infrastructure.http_client import (
    HTTPDependencyClient,
    TechnicalCaller,
    UnexpectedBody,
    json_object,
    uuid_field,
)

DEFINITIVE = {404, 409, 422}
CODE_PREFIX = "INVENTORY."


def _inventory_code(body: dict[str, Any] | None) -> str | None:
    code = body.get("code") if body else None
    if isinstance(code, str):
        return code.removeprefix(CODE_PREFIX)
    return None


class HTTPInventoryGateway:
    def __init__(
        self, *, base_url: str, timeout_seconds: float, tokens, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._caller = TechnicalCaller(
            HTTPDependencyClient(
                provider=INVENTORY,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                unavailable_cause="inventory_unreachable",
                transport=transport,
            ),
            tokens,
        )

    def _operation(self, operation: str, response: httpx.Response) -> InventoryOperationRef:
        body = json_object(response)

        if response.status_code in (200, 201):
            try:
                if body is None:
                    raise UnexpectedBody("body")
                return InventoryOperationRef(
                    id=uuid_field(body, "id"),
                    operation_type=body.get("operation_type") if isinstance(body.get("operation_type"), str) else None,
                    reverses_operation_id=uuid_field(body, "reverses_operation_id", optional=True),
                )
            except UnexpectedBody as exc:
                raise self._caller.client.unavailable(operation, outcome=f"cuerpo_inesperado:{exc}") from None

        if response.status_code in DEFINITIVE:
            raise InventoryRejection(response.status_code, _inventory_code(body), body)

        raise self._caller.client.unavailable(operation, outcome=f"estado={response.status_code}")

    def apply_entry(self, payload: dict[str, Any]) -> InventoryOperationRef:
        response = self._caller.send("inventory_entry", "POST", "/inventory-entries", json=payload)
        return self._operation("inventory_entry", response)

    def reverse_entry(self, operation_id: UUID, payload: dict[str, Any]) -> InventoryOperationRef:
        response = self._caller.send(
            "inventory_entry_reversal", "POST", f"/inventory-entries/{operation_id}/reversal", json=payload
        )
        return self._operation("inventory_entry_reversal", response)

    def find_by_key(self, company_id: UUID, operation_key: UUID) -> InventoryOperationRef | None:
        operation = "inventory_operation_by_key"
        response = self._caller.send(
            operation, "GET", f"/companies/{company_id}/inventory-operations/by-key/{operation_key}"
        )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise self._caller.client.unavailable(operation, outcome=f"estado={response.status_code}")
        return self._operation(operation, response)
