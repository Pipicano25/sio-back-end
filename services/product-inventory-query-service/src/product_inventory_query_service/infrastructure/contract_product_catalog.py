"""Product Catalog leído de sus vistas de contrato (spec 025, T073; D27).

`ContractProductCatalog` implementa `ProductCatalogPort` igual que `HTTPProductCatalog` (identidad técnica):

| Método | Fuente |
|---|---|
| `summaries` | `v1_product_summaries`, `v1_product_summary_categories` y `v1_product_summary_identifiers` (reemplazan `products/summaries/batch-lookup`, sin imagen) |
| `units` | `v1_units_of_measure` (reemplaza `units-of-measure/batch-lookup`) |
| `match_candidates`, `match_page` | siguen por API: `products/match` (FR-036) |
| `presentations` | sigue por API: la URL firmada de la imagen es de Product Catalog (FR-036) |

- Lotes de 100 ids distintos, como hoy. Un id sin fila no aparece en el resultado (el `found: false` de hoy). Igual
  que PC-1 y el `batch-lookup` de unidades, no se filtra por estado.
- Categorías en el orden de PC-1 (`is_primary DESC, code`) e identificadores en el suyo
  (`is_primary DESC, identifier_type, value`); solo los `ACTIVE`, que es lo que publica la vista.
- Una columna obligatoria vacía o cualquier error de base → `DependencyUnavailableError("product-catalog")`, el mismo
  `503` de hoy, con causa `contract:<causa>`.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import Engine

from product_inventory_query_service.application.exceptions import PRODUCT_CATALOG
from product_inventory_query_service.application.ports import (
    CatalogFilters,
    Category,
    Identifier,
    PresentationInfo,
    ProductSummary,
    Reference,
)
from product_inventory_query_service.infrastructure.contract_support import BATCH_LIMIT, ContractReader, distinct
from product_inventory_query_service.infrastructure.parsing import chunks
from product_inventory_query_service.infrastructure.product_catalog import HTTPProductCatalog

_SUMMARIES = (
    "SELECT id, canonical_name, product_type, status, brand_id, brand_code, brand_name,"
    " base_unit_id, base_unit_code, base_unit_name"
    " FROM contract.v1_product_summaries WHERE id = ANY(:ids)"
)
_CATEGORIES = (
    "SELECT global_product_id, category_id, code, name, is_primary FROM contract.v1_product_summary_categories"
    " WHERE global_product_id = ANY(:ids) ORDER BY global_product_id, is_primary DESC, code"
)
_IDENTIFIERS = (
    "SELECT global_product_id, identifier_type, value, is_primary, global_product_presentation_id"
    " FROM contract.v1_product_summary_identifiers"
    " WHERE global_product_id = ANY(:ids) ORDER BY global_product_id, is_primary DESC, identifier_type, value"
)
_UNITS = "SELECT id, code, name FROM contract.v1_units_of_measure WHERE id = ANY(:ids)"


class ContractProductCatalog:
    def __init__(self, *, engine: Engine, http: HTTPProductCatalog) -> None:
        self._reader = ContractReader(engine, PRODUCT_CATALOG)
        self._http = http

    # ------------------------------------------------------------------ vistas

    def _reference(self, operation: str, row: dict, prefix: str) -> Reference | None:
        if row.get(f"{prefix}_id") is None:
            return None
        required = self._reader.required
        return Reference(row[f"{prefix}_id"], required(operation, row, f"{prefix}_code"),
                         required(operation, row, f"{prefix}_name"))

    def _flag(self, operation: str, row: dict, name: str) -> bool:
        value = row.get(name)
        if not isinstance(value, bool):
            raise self._reader.unavailable(operation, f"cuerpo_inesperado:{name}")
        return value

    def _summaries(self, ids: list[UUID]) -> dict[UUID, ProductSummary]:
        operation = "product_summaries"
        required = self._reader.required
        result: dict[UUID, ProductSummary] = {}
        for batch in chunks(distinct(ids), BATCH_LIMIT):
            products = {row["id"]: row for row in self._reader.rows(operation, _SUMMARIES, {"ids": batch})}
            if not products:
                continue
            found = list(products)
            categories: dict[UUID, list[Category]] = defaultdict(list)
            for row in self._reader.rows(operation, _CATEGORIES, {"ids": found}):
                categories[row["global_product_id"]].append(
                    Category(required(operation, row, "category_id"), required(operation, row, "code"),
                             required(operation, row, "name"), self._flag(operation, row, "is_primary"))
                )
            identifiers: dict[UUID, list[Identifier]] = defaultdict(list)
            for row in self._reader.rows(operation, _IDENTIFIERS, {"ids": found}):
                identifiers[row["global_product_id"]].append(
                    Identifier(required(operation, row, "identifier_type"), required(operation, row, "value"),
                               self._flag(operation, row, "is_primary"), row.get("global_product_presentation_id"))
                )
            for product_id in batch:
                row = products.get(product_id)
                if row is None:
                    continue
                result[product_id] = ProductSummary(
                    id=product_id,
                    canonical_name=required(operation, row, "canonical_name"),
                    product_type=required(operation, row, "product_type"),
                    status=required(operation, row, "status"),
                    brand=self._reference(operation, row, "brand"),
                    base_unit=self._reference(operation, row, "base_unit"),
                    categories=tuple(categories.get(product_id, ())),
                    identifiers=tuple(identifiers.get(product_id, ())),
                )
        return result

    def _units(self, ids: list[UUID]) -> dict[UUID, Reference]:
        operation = "units_lookup"
        required = self._reader.required
        result: dict[UUID, Reference] = {}
        for batch in chunks(distinct(ids), BATCH_LIMIT):
            rows = {row["id"]: row for row in self._reader.rows(operation, _UNITS, {"ids": batch})}
            for unit_id in batch:
                row = rows.get(unit_id)
                if row is not None:
                    result[unit_id] = Reference(unit_id, required(operation, row, "code"), required(operation, row, "name"))
        return result

    # ------------------------------------------------------------------ puerto

    async def summaries(self, ids: list[UUID]) -> dict[UUID, ProductSummary]:
        if not ids:
            return {}
        return await self._reader.run("product_summaries", self._summaries, ids)

    async def units(self, ids: list[UUID]) -> dict[UUID, Reference]:
        if not ids:
            return {}
        return await self._reader.run("units_lookup", self._units, ids)

    async def match_candidates(self, filters: CatalogFilters, candidate_ids: list[UUID]) -> list[UUID]:
        return await self._http.match_candidates(filters, candidate_ids)

    async def match_page(self, filters: CatalogFilters, *, limit: int, after: dict | None = None):
        return await self._http.match_page(filters, limit=limit, after=after)

    async def presentations(self, ids: list[UUID], *, include_images: bool = False) -> dict[UUID, PresentationInfo]:
        return await self._http.presentations(ids, include_images=include_images)
