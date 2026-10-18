"""Partes comunes de los routers de las cuatro consultas (T107, T111, T115 y T119; contrato §1).

Orden de cada solicitud:

1. `sio-auth`: token válido (`401`) y permiso funcional del endpoint (`403`, sin revelar el permiso).
2. Parámetros estrictos (`422`) y filtros de bloques no visibles (`403`, FR-022-14).
3. Caso de uso: membresía y sucursales en OC antes de cualquier otra dependencia (`404`), plan, cursor
   (`422` si es inválido) y búsqueda.
"""

from __future__ import annotations

from typing import Annotated

from uuid import UUID

from fastapi import Path

from product_inventory_query_service.api.openapi import problem
from product_inventory_query_service.api.visibility import Block
from product_inventory_query_service.application.product_overview_service import Visibility

LISTING_ERRORS = {
    "403": problem("`FORBIDDEN`: sin el permiso funcional o con un filtro de un bloque no autorizado."),
    "404": problem("`NOT_FOUND`: empresa inexistente, sin membresía `ACTIVE` o sucursal de otra empresa."),
    "422": problem("`VALIDATION_ERROR` (parámetro inválido o desconocido) o `INVALID_CURSOR`."),
}
SUMMARY_ERRORS = {key: LISTING_ERRORS[key] for key in ("403", "404")} | {
    "422": problem("`VALIDATION_ERROR`: parámetro inválido o desconocido."),
}

PAGINATION_NOTE = (
    "Paginación por cursor sin totales: `page_size` de 1 a 20 y `next_cursor` para continuar. `partial = true` "
    "(límite de trabajo) no es el final: continúe con `next_cursor`. Si cambian los filtros, el orden o "
    "`page_size`, o el cursor vence, la consulta se reinicia con `pagination_reset = true`."
)
DEFAULT_SORTS = (
    "Orden predeterminado (`sort_applied`): `display_name:asc` sin filtros o con `search`, `internal_code` o `sku`; "
    "`canonical_name:asc` con `barcode`, `identifier` o filtros de catálogo; `company_product_id:asc` con solo "
    "`stock_state=IN_STOCK` o `minimum_state` con política. Un `sort` explícito se aplica tal cual."
)


def visibility(blocks: frozenset[Block]) -> Visibility:
    return Visibility(prices=Block.PRICES in blocks, stock=Block.STOCK in blocks, minimums=Block.MINIMUMS in blocks)


BRANCH_ROUTE_NOTE = (
    "Variante por sucursal: la sucursal va en la ruta y los datos de inventario (existencias, mínimos e "
    "indicadores) son solo de esa sucursal. Misma respuesta, filtros, permisos y paginación que la ruta de la "
    "empresa con un único `branch_id`; aquí no se admiten `branch_id` ni `scope` por consulta (`422`). Una "
    "sucursal de otra empresa responde `404`."
)

BranchInPath = Annotated[UUID, Path(description="Sucursal de la empresa (`404` si no pertenece a ella).")]
"""Parámetro de ruta `branch_id` de las variantes `/companies/{company_id}/branches/{branch_id}/…`."""
