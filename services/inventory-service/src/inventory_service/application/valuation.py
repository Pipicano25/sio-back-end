"""Consultas de valoración FIFO (FR-056; `contracts/rest-api.md` rutas 29–31).

El alcance (empresa autorizada) lo resolvió la capa API; aquí toda consulta filtra
por `company_id` (y `branch_id`) en SQL.
"""

from __future__ import annotations

from uuid import UUID

from inventory_service.application.exceptions import NotFoundError
from inventory_service.infrastructure.valuation_repository import (
    BranchValuation,
    ConsumptionRow,
    LayerRow,
    SqlValuationQueries,
)


class ValuationService:
    def __init__(self, queries: SqlValuationQueries) -> None:
        self._queries = queries

    def branch(self, company_id: UUID, branch_id: UUID, *, page: int, page_size: int) -> BranchValuation:
        return self._queries.branch_valuation(company_id, branch_id, page=page, page_size=page_size)

    def layers(
        self, company_id: UUID, branch_id: UUID, product_id: UUID, *, include_closed: bool, page: int, page_size: int
    ) -> tuple[list[LayerRow], int]:
        return self._queries.layers(
            company_id, branch_id, product_id, include_closed=include_closed, page=page, page_size=page_size
        )

    def consumptions(self, company_id: UUID, movement_id: UUID) -> list[ConsumptionRow]:
        rows = self._queries.consumptions(company_id, movement_id)
        if rows is None:
            raise NotFoundError()
        return rows
