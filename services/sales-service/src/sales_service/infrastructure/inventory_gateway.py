"""Adaptador HTTP de Inventory (contrato 012 + delta 013; research.md R-08, R-09).

- Salida: `POST /inventory-outputs` (`perm:inventory:outputs:create`), **sin `unit_cost`**: el
  costo FIFO lo informa Inventory en cada movimiento (`unit_cost` por unidad base,
  `movement_value`, `cost_known`) y Sales lo copia sin recalcularlo (P-05).
- Reverso: `POST /inventory-outputs/{operation_id}/reversal`.
- Conciliación: `GET /companies/{c}/inventory-operations/by-key/{key}` (`movements:read` +
  `platform:lookup`).
- Saldos: `POST /companies/{c}/branches/{b}/balances/lookup` (`balances:read` + `platform:lookup`).

`201`/`200` → referencia de la operación; `404`, `409` o `422` → `InventoryRejection`
(definitivo para ese contenido); `5xx`, `408`, `401` tras renovar, `403`, red, tiempo agotado o
cuerpo inesperado → `503 inventory` (se reintenta con la misma clave y la misma solicitud).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

import httpx

from sales_service.application.exceptions import INVENTORY
from sales_service.application.ports import (
    BalanceInfo,
    InventoryOperationRef,
    InventoryRejection,
    MovementCost,
)
from sales_service.infrastructure.http_client import (
    HTTPDependencyClient,
    TechnicalCaller,
    UnexpectedBody,
    decimal_field,
    json_object,
    uuid_field,
)

DEFINITIVE = {404, 409, 422}
CODE_PREFIX = "INVENTORY."
OUTPUT = "OUTPUT"
BALANCE_LIMIT = 100


def _inventory_code(body: dict[str, Any] | None) -> str | None:
    code = body.get("code") if body else None
    if isinstance(code, str):
        return code.removeprefix(CODE_PREFIX)
    return None


def _movements(body: dict[str, Any]) -> tuple[MovementCost, ...]:
    """Costo de cada movimiento de una salida; en otros tipos de operación no se leen."""
    if body.get("operation_type") != OUTPUT:
        return ()
    movements = body.get("movements")
    if not isinstance(movements, list) or not movements:
        raise UnexpectedBody("movements")
    result = []
    for movement in movements:
        if not isinstance(movement, dict):
            raise UnexpectedBody("movements")
        cost_known = movement.get("cost_known")
        if cost_known is not None and not isinstance(cost_known, bool):
            raise UnexpectedBody("cost_known")
        result.append(
            MovementCost(
                origin_detail_id=uuid_field(movement, "origin_detail_id"),
                unit_cost=decimal_field(movement, "unit_cost"),
                movement_value=decimal_field(movement, "movement_value"),
                cost_known=cost_known,
            )
        )
    return tuple(result)


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
                    movements=_movements(body),
                )
            except UnexpectedBody as exc:
                raise self._caller.client.unavailable(operation, outcome=f"cuerpo_inesperado:{exc}") from None

        if response.status_code in DEFINITIVE:
            raise InventoryRejection(response.status_code, _inventory_code(body), body)

        raise self._caller.client.unavailable(operation, outcome=f"estado={response.status_code}")

    def apply_output(self, payload: dict[str, Any]) -> InventoryOperationRef:
        response = self._caller.send("inventory_output", "POST", "/inventory-outputs", json=payload)
        return self._operation("inventory_output", response)

    def reverse_output(self, operation_id: UUID, payload: dict[str, Any]) -> InventoryOperationRef:
        response = self._caller.send(
            "inventory_output_reversal", "POST", f"/inventory-outputs/{operation_id}/reversal", json=payload
        )
        return self._operation("inventory_output_reversal", response)

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

    def lookup_balances(
        self, company_id: UUID, branch_id: UUID, product_ids: Sequence[UUID]
    ) -> dict[UUID, BalanceInfo]:
        operation = "inventory_balances_lookup"
        distinct = list(dict.fromkeys(product_ids))
        result: dict[UUID, BalanceInfo] = {}
        for start in range(0, len(distinct), BALANCE_LIMIT):
            chunk = distinct[start : start + BALANCE_LIMIT]
            response = self._caller.send(
                operation,
                "POST",
                f"/companies/{company_id}/branches/{branch_id}/balances/lookup",
                json={"company_product_ids": [str(value) for value in chunk]},
            )
            if response.status_code != 200:
                raise self._caller.client.unavailable(operation, outcome=f"estado={response.status_code}")
            body = json_object(response)
            items = body.get("items") if body else None
            if not isinstance(items, list):
                raise self._caller.client.unavailable(operation, outcome="cuerpo_inesperado")
            try:
                for item in items:
                    if not isinstance(item, dict):
                        raise UnexpectedBody("items")
                    product_id = uuid_field(item, "company_product_id")
                    result[product_id] = BalanceInfo(product_id, decimal_field(item, "quantity"))
            except UnexpectedBody as exc:
                raise self._caller.client.unavailable(operation, outcome=f"cuerpo_inesperado:{exc}") from None
        for product_id in distinct:
            result.setdefault(product_id, BalanceInfo(product_id, Decimal("0")))
        return result
