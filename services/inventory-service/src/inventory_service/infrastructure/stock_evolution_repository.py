"""Evolución de existencias para reportes (spec 023, INV-R1 por sucursal e INV-R1C consolidada; solo lectura).

Una consulta por página sobre `inventory_movements` (inmutables, en unidad base), primero por sucursal y producto y
después consolidada **por producto** sobre las sucursales indicadas (INV-R1 es el caso de una sola sucursal):

- saldo inicial: `new_balance` del último movimiento anterior a `from` por producto (`DISTINCT ON … ORDER BY
  balance_sequence DESC`, sobre `uq_inventory_movements_sequence`);
- sumas por tipo de movimiento con `created_at` en `[from, to)`;
- saldo final: `new_balance` del último movimiento del período, o el inicial si no hubo movimientos;
- consolidado: suma por producto de los saldos y movimientos de cada sucursal (`branch_count` sucursales). Nunca se
  suman productos distintos: cada fila es un producto, con su única unidad base.

Productos del alcance: con movimientos en el período o con saldo inicial mayor que cero. **Nunca** lee ni devuelve
costos (`unit_cost`, `movement_value`, `cost_known`) ni capas: el permiso `stock_evolution:read` solo cubre
cantidades (DR-11). Sin índice nuevo (DR-10): el filtro por `created_at` recorre los movimientos de la sucursal.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

_SQL = text(
    """
    WITH opening AS (
        SELECT DISTINCT ON (branch_id, company_product_id) branch_id, company_product_id,
               new_balance AS opening_quantity
        FROM inventory_movements
        WHERE company_id = :company_id AND branch_id = ANY(CAST(:branch_ids AS uuid[])) AND created_at < :from_at
          AND (CAST(:product_ids AS uuid[]) IS NULL OR company_product_id = ANY(CAST(:product_ids AS uuid[])))
        ORDER BY branch_id, company_product_id, balance_sequence DESC
    ),
    period AS (
        SELECT branch_id, company_product_id,
               sum(quantity) FILTER (WHERE movement_type = 'PURCHASE_ENTRY') AS entries,
               sum(quantity) FILTER (WHERE movement_type = 'SALE_OUTPUT') AS outputs,
               sum(quantity) FILTER (WHERE movement_type = 'ENTRY_REVERSAL') AS entry_reversals,
               sum(quantity) FILTER (WHERE movement_type = 'OUTPUT_REVERSAL') AS output_reversals,
               sum(quantity) FILTER (WHERE movement_type = 'POSITIVE_ADJUSTMENT') AS positive_adjustments,
               sum(quantity) FILTER (WHERE movement_type = 'NEGATIVE_ADJUSTMENT') AS negative_adjustments,
               count(*) AS movement_count,
               (array_agg(new_balance ORDER BY balance_sequence DESC))[1] AS closing_quantity
        FROM inventory_movements
        WHERE company_id = :company_id AND branch_id = ANY(CAST(:branch_ids AS uuid[]))
          AND created_at >= :from_at AND created_at < :to_at
          AND (CAST(:product_ids AS uuid[]) IS NULL OR company_product_id = ANY(CAST(:product_ids AS uuid[])))
        GROUP BY branch_id, company_product_id
    ),
    per_branch AS (
        -- Una fila por sucursal y producto: el saldo inicial y final de cada sucursal (nunca entre productos).
        SELECT coalesce(p.company_product_id, o.company_product_id) AS company_product_id,
               coalesce(o.opening_quantity, 0) AS opening_quantity,
               coalesce(p.entries, 0) AS entries,
               coalesce(p.outputs, 0) AS outputs,
               coalesce(p.entry_reversals, 0) AS entry_reversals,
               coalesce(p.output_reversals, 0) AS output_reversals,
               coalesce(p.positive_adjustments, 0) AS positive_adjustments,
               coalesce(p.negative_adjustments, 0) AS negative_adjustments,
               coalesce(p.closing_quantity, o.opening_quantity, 0) AS closing_quantity,
               coalesce(p.movement_count, 0) AS movement_count
        FROM period p
        FULL JOIN opening o ON o.branch_id = p.branch_id AND o.company_product_id = p.company_product_id
        WHERE p.company_product_id IS NOT NULL OR o.opening_quantity > 0
    ),
    scope AS (
        -- Consolidado por producto: sumas de las sucursales del alcance (mismo producto, misma unidad base).
        SELECT company_product_id,
               sum(opening_quantity) AS opening_quantity, sum(entries) AS entries, sum(outputs) AS outputs,
               sum(entry_reversals) AS entry_reversals, sum(output_reversals) AS output_reversals,
               sum(positive_adjustments) AS positive_adjustments, sum(negative_adjustments) AS negative_adjustments,
               sum(closing_quantity) AS closing_quantity, sum(movement_count) AS movement_count,
               count(*) AS branch_count
        FROM per_branch
        GROUP BY company_product_id
    )
    SELECT scope.*, count(*) OVER () AS total_records
    FROM scope
    ORDER BY company_product_id
    LIMIT :limit OFFSET :offset
    """
)


@dataclass(frozen=True, slots=True)
class StockEvolutionRow:
    company_product_id: UUID
    opening_quantity: Decimal
    entries: Decimal
    outputs: Decimal
    entry_reversals: Decimal
    output_reversals: Decimal
    positive_adjustments: Decimal
    negative_adjustments: Decimal
    closing_quantity: Decimal
    movement_count: int
    branch_count: int = 1


@dataclass(frozen=True, slots=True)
class StockEvolutionPage:
    items: list[StockEvolutionRow]
    total_records: int


class StockEvolutionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def page(self, company_id: UUID, branch_id: UUID, *, from_at: datetime, to_at: datetime,
             product_ids: list[UUID], page: int, page_size: int) -> StockEvolutionPage:
        """INV-R1: una sucursal (la consolidación de una sola sucursal es su propia evolución)."""
        return self.consolidated(company_id, [branch_id], from_at=from_at, to_at=to_at, product_ids=product_ids,
                                 page=page, page_size=page_size)

    def consolidated(self, company_id: UUID, branch_ids: list[UUID], *, from_at: datetime, to_at: datetime,
                     product_ids: list[UUID], page: int, page_size: int) -> StockEvolutionPage:
        """INV-R1C: por producto, sumando las sucursales indicadas, en una sola consulta por página."""
        try:
            rows = self._session.execute(
                _SQL,
                {
                    "company_id": company_id,
                    "branch_ids": [str(value) for value in branch_ids],
                    "from_at": from_at,
                    "to_at": to_at,
                    "product_ids": [str(value) for value in product_ids] or None,
                    "limit": page_size,
                    "offset": (page - 1) * page_size,
                },
            ).mappings().all()
        finally:
            self._session.rollback()
        total = rows[0]["total_records"] if rows else 0
        if not rows and page > 1:
            # Página fuera de rango: el total se informa con la primera fila (sin repetir la consulta por página).
            total = self.consolidated(company_id, branch_ids, from_at=from_at, to_at=to_at, product_ids=product_ids,
                                      page=1, page_size=1).total_records
        items = [
            StockEvolutionRow(**{name: row[name] for name in StockEvolutionRow.__dataclass_fields__}) for row in rows
        ]
        return StockEvolutionPage(items, total)
