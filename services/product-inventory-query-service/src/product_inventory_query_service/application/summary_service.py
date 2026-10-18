"""Caso de uso de `inventory-summary` (FR-022-55 a FR-022-57; D-022-9, D-022-11; T113).

Después de la autorización (tanda 0 con OC), en paralelo: CR cuenta los productos adoptados (`total_records` del
listado actual) e Inventory calcula sus indicadores operativos con INV-3. Ningún indicador se obtiene por resta o
cruce entre servicios, y este servicio **no** recorre saldos, productos ni políticas (FR-022-57): como máximo 4
llamadas (2 de OC, CR e INV-3). Un fallo de CR o de INV-3 es `503` completo.

El resumen es solo operativo: la valoración económica del inventario está fuera del alcance de la spec 022
(decisión del 2026-10-17) y no se pide a INV-3.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from product_inventory_query_service.application.authorization import authorize
from product_inventory_query_service.application.exceptions import INVENTORY, DependencyUnavailableError
from product_inventory_query_service.application.listing import Ports
from product_inventory_query_service.application.ports import InventorySummary, SummaryCounts
from product_inventory_query_service.application.request_context import RequestBudget, request_budget
from product_inventory_query_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)


@dataclass(frozen=True, slots=True)
class SummaryResult:
    company_id: UUID
    resolved_at: datetime
    adopted_products: int
    branch_ids: list[UUID]
    summary: InventorySummary


async def inventory_summary(company_id: UUID, branch_ids: list[UUID] | None, ports: Ports, *,
                            request_budget_seconds: float, max_parallel_calls: int,
                            monotonic: Callable[[], float] = time.monotonic) -> SummaryResult:
    budget = RequestBudget(request_budget_seconds, max_parallel_calls, clock=monotonic)
    resolved_at = datetime.now(UTC)
    with request_budget(budget):
        scope = await authorize(ports.oc, company_id, branch_ids)
        branches = scope.branch_ids

        async def indicators() -> InventorySummary:
            if not branches:  # sin sucursales en el alcance no hay saldos ni políticas que contar
                return InventorySummary(branches={}, consolidated=SummaryCounts(0, 0, 0, 0))
            summary = await ports.inventory.summary(company_id, branches)
            if set(summary.branches) != set(branches):
                # Una sucursal sin indicadores no se informa en cero: la respuesta de INV-3 es inválida.
                raise DependencyUnavailableError(INVENTORY, "inventory_summary", "sucursal_ausente")
            return summary

        adopted, summary = await asyncio.gather(ports.cr.count_adopted(company_id), indicators())
    logger.info("Resumen calculado sucursales=%d duracion_ms=%d", len(branches), int(budget.elapsed() * 1000))
    return SummaryResult(company_id, resolved_at, adopted, branches, summary)
