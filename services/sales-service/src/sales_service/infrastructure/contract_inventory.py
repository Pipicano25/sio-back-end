"""Inventory leído de sus vistas de contrato (spec 025, T045; D27).

Mismo puerto que `HTTPInventoryGateway`:

- `lookup_balances` lee `v1_balances` de la empresa y la sucursal en lotes de 100 (como `balances/lookup`); un
  producto sin fila vale 0, igual que hoy.
- `find_by_key` lee `v1_operations_by_key` por empresa y clave (sin fila → `None`, el `404` de hoy) y, en una salida
  (`OUTPUT`), sus movimientos de `v1_operation_movements` en el orden del API (`line_index`). Una salida sin
  movimientos es la misma indisponibilidad que hoy un cuerpo inesperado.
- `apply_output` y `reverse_output` siguen por HTTP (escrituras, FR-031).
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Engine

from sales_service.application.exceptions import INVENTORY
from sales_service.application.ports import BalanceInfo, InventoryOperationRef, MovementCost
from sales_service.infrastructure.contract_support import BATCH_LIMIT, ContractReader, distinct_ids
from sales_service.infrastructure.inventory_gateway import OUTPUT, HTTPInventoryGateway

_BALANCES = (
    "SELECT company_product_id, quantity FROM contract.v1_balances"
    " WHERE company_id = :company_id AND branch_id = :branch_id AND company_product_id = ANY(:ids)"
)
_OPERATION = (
    "SELECT operation_id, operation_type, reverses_operation_id FROM contract.v1_operations_by_key"
    " WHERE company_id = :company_id AND operation_key = :key"
)
_MOVEMENTS = (
    "SELECT origin_detail_id, unit_cost, movement_value, cost_known FROM contract.v1_operation_movements"
    " WHERE operation_id = :id AND company_id = :company_id ORDER BY line_index"
)


class ContractInventoryGateway:
    def __init__(self, *, engine: Engine, http: HTTPInventoryGateway) -> None:
        self._reader = ContractReader(engine, INVENTORY)
        self._http = http

    def apply_output(self, payload: dict[str, Any]) -> InventoryOperationRef:
        return self._http.apply_output(payload)

    def reverse_output(self, operation_id: UUID, payload: dict[str, Any]) -> InventoryOperationRef:
        return self._http.reverse_output(operation_id, payload)

    def find_by_key(self, company_id: UUID, operation_key: UUID) -> InventoryOperationRef | None:
        operation = "inventory_operation_by_key"
        row = self._reader.one(operation, _OPERATION, {"company_id": company_id, "key": operation_key})
        if row is None:
            return None
        operation_type = row.get("operation_type")
        movements: tuple[MovementCost, ...] = ()
        if operation_type == OUTPUT:
            found = self._reader.rows(operation, _MOVEMENTS, {"id": row["operation_id"], "company_id": company_id})
            if not found:
                raise self._reader.unavailable(operation, "cuerpo_inesperado:movements")
            required = self._reader.required
            movements = tuple(
                MovementCost(
                    origin_detail_id=required(operation, item, "origin_detail_id"),
                    unit_cost=required(operation, item, "unit_cost"),
                    movement_value=required(operation, item, "movement_value"),
                    cost_known=item.get("cost_known"),
                )
                for item in found
            )
        return InventoryOperationRef(
            id=self._reader.required(operation, row, "operation_id"),
            operation_type=operation_type if isinstance(operation_type, str) else None,
            reverses_operation_id=row.get("reverses_operation_id"),
            movements=movements,
        )

    def lookup_balances(
        self, company_id: UUID, branch_id: UUID, product_ids: Sequence[UUID]
    ) -> dict[UUID, BalanceInfo]:
        operation = "inventory_balances_lookup"
        distinct = distinct_ids(product_ids)
        result: dict[UUID, BalanceInfo] = {}
        for start in range(0, len(distinct), BATCH_LIMIT):
            rows = self._reader.rows(
                operation,
                _BALANCES,
                {"company_id": company_id, "branch_id": branch_id, "ids": distinct[start : start + BATCH_LIMIT]},
            )
            for row in rows:
                product_id = row["company_product_id"]
                result[product_id] = BalanceInfo(product_id, self._reader.required(operation, row, "quantity"))
        for product_id in distinct:
            result.setdefault(product_id, BalanceInfo(product_id, Decimal("0")))
        return result
