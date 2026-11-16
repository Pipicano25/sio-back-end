"""Product Catalog leído de sus vistas de contrato (spec 025, T042; D27).

Mismo puerto que `HTTPCatalogDirectory`: `v1_presentations`, `v1_products` y `v1_units_of_measure` reemplazan a
`GET /presentations/{id}`, `GET /products/{id}` y `GET /units-of-measure/{id}`. Una consulta por id, como hoy una
solicitud; sin fila → `None` (el `404` de hoy). Igual que el GET, no filtra por estado: lo decide la aplicación.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Engine

from sales_service.application.exceptions import PRODUCT_CATALOG
from sales_service.application.ports import GlobalPresentationInfo, GlobalProductInfo, UnitInfo
from sales_service.infrastructure.contract_support import ContractReader

_PRESENTATION = "SELECT code, name, base_quantity FROM contract.v1_presentations WHERE id = :id"
_PRODUCT = "SELECT base_unit_id FROM contract.v1_products WHERE id = :id"
_UNIT = "SELECT code FROM contract.v1_units_of_measure WHERE id = :id"


class ContractCatalogDirectory:
    def __init__(self, *, engine: Engine) -> None:
        self._reader = ContractReader(engine, PRODUCT_CATALOG)

    def get_presentation(self, presentation_id: UUID) -> GlobalPresentationInfo | None:
        operation = "presentation"
        row = self._reader.one(operation, _PRESENTATION, {"id": presentation_id})
        if row is None:
            return None
        required = self._reader.required
        return GlobalPresentationInfo(
            id=presentation_id,
            code=required(operation, row, "code"),
            name=required(operation, row, "name"),
            base_quantity=required(operation, row, "base_quantity"),
        )

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
