"""Nombres (Commercial Relationship, CR-1) y unidad base (Product Catalog, PC-1) por lote, con el token del usuario.

Una llamada por página y por tipo de dato (≤ 100 ids): nunca una por producto (FR-023-03).
"""

from __future__ import annotations

import logging
from uuid import UUID

from business_reporting_service.application.ports import CompanyProductInfo, UnitInfo
from business_reporting_service.infrastructure.http_client import UserCaller
from business_reporting_service.infrastructure.parsing import UnexpectedBody, items, obj, text_of, uuid_of
from business_reporting_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
MAX_BATCH = 100


class HTTPCommercialRelationship:
    def __init__(self, caller: UserCaller) -> None:
        self._caller = caller

    async def products(self, company_id: UUID, ids: list[UUID]) -> dict[UUID, CompanyProductInfo]:
        operation = "company_products_search"
        found: dict[UUID, CompanyProductInfo] = {}
        for start in range(0, len(ids), MAX_BATCH):
            batch = ids[start:start + MAX_BATCH]
            body = await self._caller.json(
                operation, "POST", f"/companies/{company_id}/company-products/search",
                json={"company_product_ids": [str(i) for i in batch], "status": "ALL", "limit": MAX_BATCH},
            )
            try:
                for item in items(body):
                    if uuid_of(item, "company_id") != company_id:
                        logger.error("Incidente de integridad: CR devolvió un producto de otra empresa")
                        continue
                    info = CompanyProductInfo(uuid_of(item, "id"), uuid_of(item, "global_product_id"),
                                              text_of(item, "internal_code", optional=True),
                                              text_of(item, "display_name"))
                    found[info.id] = info
            except UnexpectedBody:
                raise self._caller.client.unavailable(operation, "cuerpo_inesperado") from None
        return found


class HTTPProductCatalog:
    def __init__(self, caller: UserCaller) -> None:
        self._caller = caller

    async def base_units(self, global_ids: list[UUID]) -> dict[UUID, UnitInfo | None]:
        operation = "product_summaries"
        found: dict[UUID, UnitInfo | None] = {}
        unique = list(dict.fromkeys(global_ids))
        for start in range(0, len(unique), MAX_BATCH):
            batch = unique[start:start + MAX_BATCH]
            body = await self._caller.json(operation, "POST", "/products/summaries/batch-lookup",
                                           json={"ids": [str(i) for i in batch]})
            try:
                for item in items(body):
                    unit = item.get("base_unit")
                    found[uuid_of(item, "id")] = None if unit is None else UnitInfo(
                        uuid_of(obj(unit), "id"), text_of(unit, "code"), text_of(unit, "name"))
            except UnexpectedBody:
                raise self._caller.client.unavailable(operation, "cuerpo_inesperado") from None
        return found
