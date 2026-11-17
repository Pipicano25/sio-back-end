"""Productos empresariales leídos de la vista de contrato de Commercial Relationship (spec 025, T064; D27).

Mismo puerto que `HTTPCompanyProductDirectory`: `lookup` lee `contract.v1_company_products` en lotes de 100 (como
`company-products/batch-lookup`, hoy con la identidad técnica de Inventory). Igual que ese endpoint, no filtra por
empresa: la aplicación compara `company_id`. Un producto sin fila queda ausente del resultado (`found=false`).
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import Engine

from inventory_service.application.exceptions import COMMERCIAL_RELATIONSHIP
from inventory_service.application.ports import CompanyProductInfo
from inventory_service.infrastructure.contract_support import BATCH_LIMIT, ContractReader, distinct_ids

_PRODUCTS = (
    "SELECT id, company_id, status, inventory_control_enabled FROM contract.v1_company_products WHERE id = ANY(:ids)"
)


class ContractCompanyProductDirectory:
    def __init__(self, *, engine: Engine) -> None:
        self._reader = ContractReader(engine, COMMERCIAL_RELATIONSHIP)

    def lookup(self, product_ids: Iterable[UUID]) -> dict[UUID, CompanyProductInfo]:
        operation = "batch_lookup"
        ids = distinct_ids(list(product_ids))
        found: dict[UUID, CompanyProductInfo] = {}
        for start in range(0, len(ids), BATCH_LIMIT):
            for row in self._reader.rows(operation, _PRODUCTS, {"ids": ids[start : start + BATCH_LIMIT]}):
                control = row.get("inventory_control_enabled")
                if not isinstance(control, bool):
                    raise self._reader.unavailable(operation, "cuerpo_inesperado:inventory_control_enabled")
                found[row["id"]] = CompanyProductInfo(
                    id=row["id"],
                    company_id=self._reader.required(operation, row, "company_id"),
                    status=self._reader.required(operation, row, "status"),
                    inventory_control_enabled=control,
                )
        return found
