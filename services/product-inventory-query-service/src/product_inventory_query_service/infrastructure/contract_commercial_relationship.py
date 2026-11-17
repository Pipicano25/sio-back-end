"""Commercial Relationship leído de sus vistas de contrato (spec 025, T073; D27).

`ContractCommercialRelationship` implementa `CommercialRelationshipPort` igual que `HTTPCommercialRelationship`
(identidad técnica):

| Método | Fuente |
|---|---|
| `count_adopted` | `v1_company_products` (reemplaza `total_records` de `GET /companies/{c}/company-products?status=ACTIVE&inventory_control_enabled=true`) |
| `presentations_by_products` | `v1_company_product_presentations` (reemplaza `company-product-presentations/by-products` con `status=ALL`) |
| `search_products` | sigue por API: `company-products/search` (FR-036) |
| `resolve_prices` | sigue por API: `applicable-prices/resolve` (FR-036) |

- Siempre se filtra por la empresa de la ruta (`company_id = :c`): una fila de otra empresa nunca llega, igual que el
  descarte por integridad de hoy.
- `presentations_by_products`: lotes de 100 productos distintos, cada lote en el orden de CR-2
  (`company_product_id, id`), en cualquier estado.
- Una columna obligatoria vacía o cualquier error de base → `DependencyUnavailableError("commercial-relationship")`,
  el mismo `503` de hoy, con causa `contract:<causa>`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Engine

from product_inventory_query_service.application.exceptions import COMMERCIAL_RELATIONSHIP
from product_inventory_query_service.application.ports import (
    CompanyPresentation,
    CompanyProduct,
    PriceLine,
    PriceResult,
    ProductCriteria,
)
from product_inventory_query_service.infrastructure.commercial_relationship import HTTPCommercialRelationship
from product_inventory_query_service.infrastructure.contract_support import BATCH_LIMIT, ContractReader, distinct
from product_inventory_query_service.infrastructure.parsing import chunks

_ADOPTED = (
    "SELECT count(*) AS total FROM contract.v1_company_products"
    " WHERE company_id = :company_id AND status = 'ACTIVE' AND inventory_control_enabled"
)
_BY_PRODUCTS = (
    "SELECT id, company_id, company_product_id, global_product_presentation_id, internal_code, sku, reference_code,"
    " is_sellable, status FROM contract.v1_company_product_presentations"
    " WHERE company_id = :company_id AND company_product_id = ANY(:ids) ORDER BY company_product_id, id"
)


class ContractCommercialRelationship:
    def __init__(self, *, engine: Engine, http: HTTPCommercialRelationship) -> None:
        self._reader = ContractReader(engine, COMMERCIAL_RELATIONSHIP)
        self._http = http

    # ------------------------------------------------------------------ vistas

    def _count_adopted(self, company_id: UUID) -> int:
        operation = "adopted_count"
        rows = self._reader.rows(operation, _ADOPTED, {"company_id": company_id})
        return int(self._reader.required(operation, rows[0], "total"))

    def _presentations(self, company_id: UUID, company_product_ids: list[UUID]) -> list[CompanyPresentation]:
        operation = "presentations_by_products"
        required = self._reader.required
        found: list[CompanyPresentation] = []
        for batch in chunks(distinct(company_product_ids), BATCH_LIMIT):
            for row in self._reader.rows(operation, _BY_PRODUCTS, {"company_id": company_id, "ids": batch}):
                is_sellable = row.get("is_sellable")
                if not isinstance(is_sellable, bool):
                    raise self._reader.unavailable(operation, "cuerpo_inesperado:is_sellable")
                found.append(
                    CompanyPresentation(
                        id=required(operation, row, "id"),
                        company_id=required(operation, row, "company_id"),
                        company_product_id=required(operation, row, "company_product_id"),
                        global_product_presentation_id=required(operation, row, "global_product_presentation_id"),
                        internal_code=row.get("internal_code"),
                        sku=row.get("sku"),
                        reference_code=row.get("reference_code"),
                        is_sellable=is_sellable,
                        status=required(operation, row, "status"),
                    )
                )
        return found

    # ------------------------------------------------------------------ puerto

    async def count_adopted(self, company_id: UUID) -> int:
        return await self._reader.run("adopted_count", self._count_adopted, company_id)

    async def presentations_by_products(self, company_id: UUID, company_product_ids: list[UUID]) -> list[CompanyPresentation]:
        if not company_product_ids:
            return []
        return await self._reader.run("presentations_by_products", self._presentations, company_id,
                                      company_product_ids)

    async def search_products(
        self,
        company_id: UUID,
        criteria: ProductCriteria,
        *,
        sort_key: str,
        descending: bool,
        limit: int,
        after: dict | None = None,
        company_product_ids: list[UUID] | None = None,
        global_product_ids: list[UUID] | None = None,
    ) -> tuple[list[CompanyProduct], bool]:
        return await self._http.search_products(
            company_id, criteria, sort_key=sort_key, descending=descending, limit=limit, after=after,
            company_product_ids=company_product_ids, global_product_ids=global_product_ids,
        )

    async def resolve_prices(self, company_id: UUID, lines: list[PriceLine]) -> list[PriceResult]:
        return await self._http.resolve_prices(company_id, lines)
