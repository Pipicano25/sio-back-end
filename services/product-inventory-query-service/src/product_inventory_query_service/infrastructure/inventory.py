"""Adaptador de Inventory con la identidad técnica (`contracts/inventory.md`).

`balances/lookup` devuelve `inventory_value` y `average_unit_cost`: este adaptador **los descarta** y el dominio
nunca los recibe (FR-022-15, RC-022-2). Un saldo con `balance_sequence = 0` es un producto sin registro de saldo en
la sucursal (`NOT_REGISTERED`). Toda fila de otra empresa o sucursal se descarta y se registra (FR-022-12).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from product_inventory_query_service.application.ports import (
    Balance,
    BelowMinimumPair,
    InventorySummary,
    Policy,
    SummaryCounts,
)
from product_inventory_query_service.infrastructure.http_client import TechnicalCaller
from product_inventory_query_service.infrastructure.parsing import (
    UnexpectedBody,
    bool_of,
    chunks,
    decimal_of,
    int_of,
    items,
    obj,
    position_of,
    uuid_of,
)
from product_inventory_query_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
_COUNTS = ("products_with_positive_balance", "products_with_zero_balance", "products_with_policy", "products_below_minimum")


def _counts(data: dict) -> SummaryCounts:
    """Solo los indicadores operativos; cualquier campo económico de la respuesta se ignora."""
    return SummaryCounts(**{name: int_of(data, name) for name in _COUNTS})


class HTTPInventory:
    def __init__(self, caller: TechnicalCaller) -> None:
        self._caller = caller

    def _bad(self, operation: str):
        return self._caller.client.unavailable(operation, "cuerpo_inesperado")

    async def balances(self, company_id: UUID, branch_id: UUID, ids: list[UUID]) -> dict[UUID, Balance]:
        operation = "balances_lookup"

        async def one(batch: list[UUID]) -> list[Balance]:
            payload = await self._caller.json(
                operation, "POST", f"/companies/{company_id}/branches/{branch_id}/balances/lookup",
                json={"company_product_ids": [str(i) for i in batch]},
            )
            try:
                found = []
                for item in items(payload):
                    if uuid_of(item, "company_id") != company_id or uuid_of(item, "branch_id") != branch_id:
                        logger.error("Incidente de integridad: Inventory devolvió un saldo de otra empresa o sucursal")
                        continue
                    # Solo se toman cantidad y secuencia: `inventory_value` y `average_unit_cost` se descartan aquí.
                    found.append(
                        Balance(
                            company_product_id=uuid_of(item, "company_product_id"),
                            branch_id=branch_id,
                            quantity=decimal_of(item, "quantity"),
                            registered=int_of(item, "balance_sequence") > 0,
                        )
                    )
                return found
            except UnexpectedBody:
                raise self._bad(operation) from None

        unique = list(dict.fromkeys(ids))
        if not unique:
            return {}
        results = await asyncio.gather(*(one(batch) for batch in chunks(unique)))
        return {balance.company_product_id: balance for batch in results for balance in batch}

    async def policies(self, company_id: UUID, branch_id: UUID, ids: list[UUID]) -> dict[UUID, Policy]:
        operation = "policies_lookup"

        async def one(batch: list[UUID]) -> list[Policy]:
            payload = await self._caller.json(
                operation, "POST", f"/companies/{company_id}/branches/{branch_id}/inventory-policies/lookup",
                json={"company_product_ids": [str(i) for i in batch]},
            )
            try:
                found = []
                for item in items(payload):
                    policy = item.get("policy")
                    if policy is None:
                        continue
                    found.append(Policy(uuid_of(item, "company_product_id"), branch_id, decimal_of(obj(policy), "minimum_stock")))
                return found
            except UnexpectedBody:
                raise self._bad(operation) from None

        unique = list(dict.fromkeys(ids))
        if not unique:
            return {}
        results = await asyncio.gather(*(one(batch) for batch in chunks(unique)))
        return {policy.company_product_id: policy for batch in results for policy in batch}

    async def product_set(self, company_id, branch_ids, *, stock_state, minimum_state, limit, after=None):
        operation = "product_sets"
        body: dict[str, Any] = {"branch_ids": [str(b) for b in branch_ids], "limit": limit}
        if stock_state is not None:
            body["stock_state"] = stock_state
        if minimum_state is not None:
            body["minimum_state"] = minimum_state
        if after is not None:
            body["after"] = after
        payload = await self._caller.json(operation, "POST", f"/companies/{company_id}/inventory-product-sets", json=body)
        try:
            page = [(uuid_of(item, "company_product_id"), position_of(item)) for item in items(payload)]
            return page, bool_of(obj(payload), "has_more")
        except UnexpectedBody:
            raise self._bad(operation) from None

    async def below_minimum_pairs(self, company_id, branch_ids, *, limit, after=None):
        operation = "below_minimum_pairs"
        body: dict[str, Any] = {
            "branch_ids": [str(b) for b in branch_ids],
            "minimum_state": "BELOW_MINIMUM",
            "unit": "PAIRS",
            "limit": limit,
            **({"after": after} if after else {}),
        }
        payload = await self._caller.json(operation, "POST", f"/companies/{company_id}/inventory-product-sets", json=body)
        allowed = set(branch_ids)
        try:
            pairs = []
            for item in items(payload):
                pair = BelowMinimumPair(
                    company_product_id=uuid_of(item, "company_product_id"),
                    branch_id=uuid_of(item, "branch_id"),
                    base_quantity=decimal_of(item, "base_quantity"),
                    minimum_stock=decimal_of(item, "minimum_stock"),
                    shortfall=decimal_of(item, "shortfall"),
                    position=position_of(item),
                )
                if pair.branch_id not in allowed:
                    logger.error("Incidente de integridad: Inventory devolvió un par de una sucursal no pedida")
                    continue
                pairs.append(pair)
            return pairs, bool_of(obj(payload), "has_more")
        except UnexpectedBody:
            raise self._bad(operation) from None

    async def summary(self, company_id: UUID, branch_ids: list[UUID]) -> InventorySummary:
        """INV-3 sin `include_valuation` (por defecto `false`): la valoración está fuera de la spec 022."""
        operation = "inventory_summary"
        payload = await self._caller.json(
            operation, "POST", f"/companies/{company_id}/inventory-summary",
            json={"branch_ids": [str(b) for b in branch_ids]},
        )
        try:
            branches = {uuid_of(item, "branch_id"): _counts(item) for item in items(payload, "branches")}
            consolidated = _counts(obj(obj(payload).get("consolidated")))
        except UnexpectedBody:
            raise self._bad(operation) from None
        if set(branches) - set(branch_ids):
            logger.error("Incidente de integridad: Inventory devolvió indicadores de una sucursal no pedida")
            raise self._bad(operation)
        return InventorySummary(branches=branches, consolidated=consolidated)
