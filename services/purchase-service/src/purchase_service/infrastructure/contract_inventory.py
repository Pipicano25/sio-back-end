"""Inventory leído de su vista de contrato (spec 025, T053; D27).

Mismo puerto que `HTTPInventoryGateway`: `find_by_key` lee `v1_operations_by_key` por empresa y clave (sin fila →
`None`, el `404` de hoy; Purchase no lee los movimientos). `apply_entry` y `reverse_entry` siguen por HTTP
(escrituras, FR-031).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Engine

from purchase_service.application.exceptions import INVENTORY
from purchase_service.application.ports import InventoryOperationRef
from purchase_service.infrastructure.contract_support import ContractReader
from purchase_service.infrastructure.inventory_gateway import HTTPInventoryGateway

_OPERATION = (
    "SELECT operation_id, operation_type, reverses_operation_id FROM contract.v1_operations_by_key"
    " WHERE company_id = :company_id AND operation_key = :key"
)


class ContractInventoryGateway:
    def __init__(self, *, engine: Engine, http: HTTPInventoryGateway) -> None:
        self._reader = ContractReader(engine, INVENTORY)
        self._http = http

    def apply_entry(self, payload: dict[str, Any]) -> InventoryOperationRef:
        return self._http.apply_entry(payload)

    def reverse_entry(self, operation_id: UUID, payload: dict[str, Any]) -> InventoryOperationRef:
        return self._http.reverse_entry(operation_id, payload)

    def find_by_key(self, company_id: UUID, operation_key: UUID) -> InventoryOperationRef | None:
        operation = "inventory_operation_by_key"
        row = self._reader.one(operation, _OPERATION, {"company_id": company_id, "key": operation_key})
        if row is None:
            return None
        operation_type = row.get("operation_type")
        return InventoryOperationRef(
            id=self._reader.required(operation, row, "operation_id"),
            operation_type=operation_type if isinstance(operation_type, str) else None,
            reverses_operation_id=row.get("reverses_operation_id"),
        )
