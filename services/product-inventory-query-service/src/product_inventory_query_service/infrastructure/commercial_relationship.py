"""Adaptador de Commercial Relationship con la identidad técnica (`contracts/commercial-relationship.md`).

Toda fila con un `company_id` distinto de la empresa de la ruta se descarta y se registra como incidente de
integridad (FR-022-12). La `position` de CR-1 se conserva sin modificarla (research R-06).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from product_inventory_query_service.application.ports import (
    CompanyPresentation,
    CompanyProduct,
    PriceLine,
    PriceResult,
    ProductCriteria,
)
from product_inventory_query_service.infrastructure.http_client import TechnicalCaller
from product_inventory_query_service.infrastructure.parsing import (
    UnexpectedBody,
    bool_of,
    chunks,
    datetime_of,
    int_of,
    items,
    obj,
    position_of,
    text_of,
    uuid_of,
)
from product_inventory_query_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)


def _incident(kind: str) -> None:
    logger.error("Incidente de integridad: Commercial Relationship devolvió %s de otra empresa", kind)


class HTTPCommercialRelationship:
    def __init__(self, caller: TechnicalCaller) -> None:
        self._caller = caller

    def _bad(self, operation: str):
        return self._caller.client.unavailable(operation, "cuerpo_inesperado")

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
        operation = "company_products_search"
        body: dict[str, Any] = {
            "status": criteria.status,
            "sort": {"key": sort_key, "direction": "desc" if descending else "asc"},
            "limit": limit,
        }
        for name in ("search", "internal_code", "sku", "inventory_control_enabled"):
            value = getattr(criteria, name)
            if value is not None:
                body[name] = value
        if after is not None:
            body["after"] = after
        if company_product_ids is not None:
            body["company_product_ids"] = [str(i) for i in company_product_ids]
        if global_product_ids is not None:
            body["global_product_ids"] = [str(i) for i in global_product_ids]

        payload = await self._caller.json(operation, "POST", f"/companies/{company_id}/company-products/search", json=body)
        try:
            products = []
            for item in items(payload):
                product = CompanyProduct(
                    id=uuid_of(item, "id"),
                    company_id=uuid_of(item, "company_id"),
                    global_product_id=uuid_of(item, "global_product_id"),
                    internal_code=text_of(item, "internal_code"),
                    reference_code=text_of(item, "reference_code", optional=True),
                    display_name=text_of(item, "display_name"),
                    status=text_of(item, "status"),
                    is_sellable=bool_of(item, "is_sellable"),
                    is_purchasable=bool_of(item, "is_purchasable"),
                    inventory_control_enabled=bool_of(item, "inventory_control_enabled"),
                    created_at=datetime_of(item, "created_at"),
                    position=position_of(item),
                )
                if product.company_id != company_id:
                    _incident("un producto")
                    continue
                products.append(product)
            return products, bool_of(obj(payload), "has_more")
        except UnexpectedBody:
            raise self._bad(operation) from None

    async def presentations_by_products(self, company_id: UUID, company_product_ids: list[UUID]) -> list[CompanyPresentation]:
        operation = "presentations_by_products"

        async def one(batch: list[UUID]) -> list[CompanyPresentation]:
            payload = await self._caller.json(
                operation, "POST", f"/companies/{company_id}/company-product-presentations/by-products",
                json={"company_product_ids": [str(i) for i in batch], "status": "ALL"},
            )
            try:
                found = []
                for item in items(payload):
                    presentation = CompanyPresentation(
                        id=uuid_of(item, "id"),
                        company_id=uuid_of(item, "company_id"),
                        company_product_id=uuid_of(item, "company_product_id"),
                        global_product_presentation_id=uuid_of(item, "global_product_presentation_id"),
                        internal_code=text_of(item, "internal_code", optional=True),
                        sku=text_of(item, "sku", optional=True),
                        reference_code=text_of(item, "reference_code", optional=True),
                        is_sellable=bool_of(item, "is_sellable"),
                        status=text_of(item, "status"),
                    )
                    if presentation.company_id != company_id:
                        _incident("una presentación")
                        continue
                    found.append(presentation)
                return found
            except UnexpectedBody:
                raise self._bad(operation) from None

        results = await asyncio.gather(*(one(batch) for batch in chunks(list(dict.fromkeys(company_product_ids)))))
        return [presentation for batch in results for presentation in batch]

    async def resolve_prices(self, company_id: UUID, lines: list[PriceLine]) -> list[PriceResult]:
        operation = "applicable_prices"

        async def one(batch: list[PriceLine]) -> list[PriceResult]:
            payload = await self._caller.json(
                operation, "POST", f"/companies/{company_id}/applicable-prices/resolve",
                json={"lines": [
                    {
                        "line_id": str(line.company_product_presentation_id),
                        "company_product_id": str(line.company_product_id),
                        "company_product_presentation_id": str(line.company_product_presentation_id),
                        **({"price_list_id": str(line.price_list_id)} if line.price_list_id else {}),
                    }
                    for line in batch
                ]},
            )
            try:
                return [
                    PriceResult(
                        company_product_presentation_id=UUID(text_of(item, "line_id")),
                        resolution=text_of(item, "resolution"),
                        unit_price=text_of(item, "unit_price", optional=True),
                        currency_code=text_of(item, "currency_code", optional=True),
                        price_list_id=uuid_of(item, "price_list_id", optional=True),
                        price_list_item_id=uuid_of(item, "price_list_item_id", optional=True),
                    )
                    for item in items(payload)
                ]
            except (UnexpectedBody, ValueError):
                raise self._bad(operation) from None

        results = await asyncio.gather(*(one(batch) for batch in chunks(lines)))
        return [price for batch in results for price in batch]

    async def count_adopted(self, company_id: UUID) -> int:
        operation = "adopted_count"
        payload = await self._caller.json(
            operation, "GET", f"/companies/{company_id}/company-products",
            params={"status": "ACTIVE", "inventory_control_enabled": "true", "page_size": 1},
        )
        try:
            return int_of(obj(payload), "total_records")
        except UnexpectedBody:
            raise self._bad(operation) from None
