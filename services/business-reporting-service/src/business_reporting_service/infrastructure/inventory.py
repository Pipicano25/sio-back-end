"""Adaptador de la evolución de existencias de Inventory (INV-R1 e INV-R1C) con el token del usuario (DR-07, DR-11).

El contrato de INV-R1 no tiene costos; si el cuerpo trajera alguno, se descarta sin leerlo y se registra como
incidente (nunca llega a la respuesta del reporte).
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from business_reporting_service.application.ports import StockEvolution, StockEvolutionPage
from business_reporting_service.infrastructure.http_client import UserCaller
from business_reporting_service.infrastructure.parsing import UnexpectedBody, decimal_of, int_of, items, obj, uuid_of
from business_reporting_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
QUANTITIES = ("opening_quantity", "entries", "outputs", "entry_reversals", "output_reversals",
              "positive_adjustments", "negative_adjustments", "closing_quantity")
COST_KEYS = {"unit_cost", "movement_value", "cost_known", "inventory_value", "average_unit_cost"}


class HTTPInventory:
    def __init__(self, caller: UserCaller) -> None:
        self._caller = caller

    async def stock_evolution(self, company_id: UUID, branch_id: UUID, *, from_at: datetime, to_at: datetime,
                              product_ids: list[UUID], page: int, page_size: int) -> StockEvolutionPage:
        operation = "stock_evolution"
        params = [("from", from_at.isoformat()), ("to", to_at.isoformat()), ("page", str(page)),
                  ("page_size", str(page_size))] + [("company_product_id", str(p)) for p in product_ids]
        body = await self._caller.json(operation, "GET",
                                       f"/companies/{company_id}/branches/{branch_id}/stock-evolution", params=params)
        try:
            head = obj(body)
            if uuid_of(head, "company_id") != company_id or uuid_of(head, "branch_id") != branch_id:
                logger.error("Incidente de integridad: Inventory devolvió otra empresa o sucursal")
                raise self._caller.client.unavailable(operation, "integridad")
            rows = _rows(body, consolidated=False)
            total = int_of(head, "total_records")
        except UnexpectedBody:
            raise self._caller.client.unavailable(operation, "cuerpo_inesperado") from None
        return StockEvolutionPage(rows, total)

    async def consolidated_stock_evolution(self, company_id: UUID, branch_ids: list[UUID], *, from_at: datetime,
                                           to_at: datetime, product_ids: list[UUID], page: int,
                                           page_size: int) -> StockEvolutionPage:
        """INV-R1C: una sola consulta por página, consolidada por producto en Inventory."""
        operation = "consolidated_stock_evolution"
        params = [("from", from_at.isoformat()), ("to", to_at.isoformat()), ("page", str(page)),
                  ("page_size", str(page_size))] + [("branch_id", str(b)) for b in branch_ids]
        params += [("company_product_id", str(p)) for p in product_ids]
        body = await self._caller.json(operation, "GET", f"/companies/{company_id}/stock-evolution", params=params)
        try:
            head = obj(body)
            returned = {uuid_of({"id": value}, "id") for value in head.get("branch_ids", [])}
            if uuid_of(head, "company_id") != company_id or not returned <= set(branch_ids):
                logger.error("Incidente de integridad: Inventory devolvió otra empresa o sucursales no pedidas")
                raise self._caller.client.unavailable(operation, "integridad")
            rows = _rows(body, consolidated=True)
            total = int_of(head, "total_records")
        except UnexpectedBody:
            raise self._caller.client.unavailable(operation, "cuerpo_inesperado") from None
        return StockEvolutionPage(rows, total)


def _rows(body, *, consolidated: bool) -> list[StockEvolution]:
    rows = []
    for item in items(body):
        if COST_KEYS & set(item):
            logger.error("Incidente: Inventory devolvió campos de costo en la evolución de existencias; se descartan")
        rows.append(StockEvolution(uuid_of(item, "company_product_id"), *(decimal_of(item, name) for name in QUANTITIES),
                                   int_of(item, "movement_count"),
                                   int_of(item, "branch_count") if consolidated else 1))
    return rows
