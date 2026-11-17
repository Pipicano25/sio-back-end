"""Inventory leído de sus vistas de contrato (spec 025, T073; D27).

`ContractInventory` implementa `InventoryPort` igual que `HTTPInventory` (identidad técnica):

| Método | Fuente |
|---|---|
| `balances` | `v1_balances` (reemplaza `branches/{b}/balances/lookup`) |
| `policies` | `v1_inventory_policies` (reemplaza `branches/{b}/inventory-policies/lookup`, INV-1) |
| `product_set`, `below_minimum_pairs` | siguen por API: `inventory-product-sets` (INV-2, FR-036) |
| `summary` | sigue por API: `inventory-summary` (INV-3, FR-036) |

- Siempre se filtra por la empresa y la sucursal de la ruta; lotes de 100 productos distintos, como hoy.
- Saldos: la vista solo tiene los productos con saldo registrado. Un producto sin fila vale `0.0000` y
  `registered = False`, que es lo que hoy responde `balances/lookup` (`quantity = "0.0000"`,
  `balance_sequence = 0`). `inventory_value` y `average_unit_cost` no se leen (FR-022-15).
- Políticas: solo la política activa; un producto sin fila no aparece (el `policy: null` de hoy).
- Una columna obligatoria vacía o cualquier error de base → `DependencyUnavailableError("inventory")`, el mismo `503`
  de hoy, con causa `contract:<causa>`.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Engine

from product_inventory_query_service.application.exceptions import INVENTORY
from product_inventory_query_service.application.ports import Balance, BelowMinimumPair, InventorySummary, Policy
from product_inventory_query_service.infrastructure.contract_support import BATCH_LIMIT, ContractReader, distinct
from product_inventory_query_service.infrastructure.inventory import HTTPInventory
from product_inventory_query_service.infrastructure.parsing import chunks

ZERO = Decimal("0.0000")

_BALANCES = (
    "SELECT company_product_id, quantity, balance_sequence FROM contract.v1_balances"
    " WHERE company_id = :company_id AND branch_id = :branch_id AND company_product_id = ANY(:ids)"
)
_POLICIES = (
    "SELECT company_product_id, minimum_stock FROM contract.v1_inventory_policies"
    " WHERE company_id = :company_id AND branch_id = :branch_id AND company_product_id = ANY(:ids)"
)


class ContractInventory:
    def __init__(self, *, engine: Engine, http: HTTPInventory) -> None:
        self._reader = ContractReader(engine, INVENTORY)
        self._http = http

    # ------------------------------------------------------------------ vistas

    def _balances(self, company_id: UUID, branch_id: UUID, ids: list[UUID]) -> dict[UUID, Balance]:
        operation = "balances_lookup"
        required = self._reader.required
        result: dict[UUID, Balance] = {}
        for batch in chunks(distinct(ids), BATCH_LIMIT):
            params = {"company_id": company_id, "branch_id": branch_id, "ids": batch}
            rows = {row["company_product_id"]: row for row in self._reader.rows(operation, _BALANCES, params)}
            for product_id in batch:
                row = rows.get(product_id)
                if row is None:
                    result[product_id] = Balance(product_id, branch_id, ZERO, registered=False)
                    continue
                sequence = required(operation, row, "balance_sequence")
                result[product_id] = Balance(product_id, branch_id, required(operation, row, "quantity"),
                                             registered=int(sequence) > 0)
        return result

    def _policies(self, company_id: UUID, branch_id: UUID, ids: list[UUID]) -> dict[UUID, Policy]:
        operation = "policies_lookup"
        result: dict[UUID, Policy] = {}
        for batch in chunks(distinct(ids), BATCH_LIMIT):
            params = {"company_id": company_id, "branch_id": branch_id, "ids": batch}
            rows = {row["company_product_id"]: row for row in self._reader.rows(operation, _POLICIES, params)}
            for product_id in batch:
                row = rows.get(product_id)
                if row is not None:
                    result[product_id] = Policy(product_id, branch_id,
                                                self._reader.required(operation, row, "minimum_stock"))
        return result

    # ------------------------------------------------------------------ puerto

    async def balances(self, company_id: UUID, branch_id: UUID, ids: list[UUID]) -> dict[UUID, Balance]:
        if not ids:
            return {}
        return await self._reader.run("balances_lookup", self._balances, company_id, branch_id, ids)

    async def policies(self, company_id: UUID, branch_id: UUID, ids: list[UUID]) -> dict[UUID, Policy]:
        if not ids:
            return {}
        return await self._reader.run("policies_lookup", self._policies, company_id, branch_id, ids)

    async def product_set(self, company_id, branch_ids, *, stock_state, minimum_state, limit, after=None):
        return await self._http.product_set(company_id, branch_ids, stock_state=stock_state,
                                            minimum_state=minimum_state, limit=limit, after=after)

    async def below_minimum_pairs(
        self, company_id, branch_ids, *, limit, after=None
    ) -> tuple[list[BelowMinimumPair], bool]:
        return await self._http.below_minimum_pairs(company_id, branch_ids, limit=limit, after=after)

    async def summary(self, company_id: UUID, branch_ids: list[UUID]) -> InventorySummary:
        return await self._http.summary(company_id, branch_ids)
