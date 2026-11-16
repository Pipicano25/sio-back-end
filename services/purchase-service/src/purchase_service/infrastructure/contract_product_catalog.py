"""Product Catalog leído de sus vistas de contrato (spec 025, T053; D27).

Mismo puerto que `HTTPCatalogDirectory`: `v1_presentations`, `v1_products` y `v1_units_of_measure` reemplazan a
`GET /presentations/{id}`, `presentations/batch-lookup`, `GET /products/{id}` y `GET /units-of-measure/{id}`. Sin
fila → `None` o ausente (el `404` o `found=false` de hoy). Igual que el GET, no filtra por estado.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Engine

from purchase_service.application.exceptions import PRODUCT_CATALOG
from purchase_service.application.ports import GlobalPresentationInfo, GlobalProductInfo, UnitInfo
from purchase_service.infrastructure.contract_support import BATCH_LIMIT, ContractReader, distinct_ids

_PRESENTATION = "SELECT id, code, name, base_quantity FROM contract.v1_presentations WHERE id = :id"
_PRESENTATIONS = "SELECT id, code, name, base_quantity FROM contract.v1_presentations WHERE id = ANY(:ids)"
_PRODUCT = "SELECT base_unit_id FROM contract.v1_products WHERE id = :id"
_UNIT = "SELECT code FROM contract.v1_units_of_measure WHERE id = :id"


class ContractCatalogDirectory:
    def __init__(self, *, engine: Engine) -> None:
        self._reader = ContractReader(engine, PRODUCT_CATALOG)

    def _presentation(self, operation: str, row: dict) -> GlobalPresentationInfo:
        required = self._reader.required
        return GlobalPresentationInfo(
            id=row["id"],
            code=required(operation, row, "code"),
            name=required(operation, row, "name"),
            base_quantity=required(operation, row, "base_quantity"),
        )

    def get_presentation(self, presentation_id: UUID) -> GlobalPresentationInfo | None:
        operation = "presentation"
        row = self._reader.one(operation, _PRESENTATION, {"id": presentation_id})
        return None if row is None else self._presentation(operation, row)

    def lookup_presentations(self, ids: Sequence[UUID]) -> dict[UUID, GlobalPresentationInfo]:
        operation = "presentations_batch"
        distinct = distinct_ids(ids)
        result: dict[UUID, GlobalPresentationInfo] = {}
        for start in range(0, len(distinct), BATCH_LIMIT):
            for row in self._reader.rows(operation, _PRESENTATIONS, {"ids": distinct[start : start + BATCH_LIMIT]}):
                result[row["id"]] = self._presentation(operation, row)
        return result

    def get_product(self, product_id: UUID) -> GlobalProductInfo | None:
        operation = "product"
        row = self._reader.one(operation, _PRODUCT, {"id": product_id})
        if row is None:
            return None
        return GlobalProductInfo(id=product_id, base_unit_id=self._reader.required(operation, row, "base_unit_id"))

    def get_unit(self, unit_id: UUID) -> UnitInfo | None:
        operation = "unit_of_measure"
        row = self._reader.one(operation, _UNIT, {"id": unit_id})
        if row is None:
            return None
        return UnitInfo(id=unit_id, code=self._reader.required(operation, row, "code"))
