"""Adaptador de Product Catalog con la identidad técnica (`contracts/product-catalog.md`).

PC es un catálogo global: no tiene `company_id`. Sus datos solo se agregan a productos que CR ya devolvió para la
empresa (FR-022-12); `image_url` se copia tal como la construye PC (research R-13).

El código, el nombre, el factor y la imagen de cada presentación vienen de `presentations/batch-lookup` (PC-3,
specs 021 y 024) que la cuenta técnica ya lee con `products:read`: CR-2 solo trae los datos de la empresa.
Spec 024: la imagen es de la presentación; los campos de imagen de PC-1 (transitorios) ya no se leen.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from product_inventory_query_service.application.ports import (
    CatalogFilters,
    Category,
    Identifier,
    PresentationImage,
    PresentationInfo,
    ProductSummary,
    Reference,
)
from product_inventory_query_service.infrastructure.http_client import TechnicalCaller
from product_inventory_query_service.infrastructure.parsing import (
    UnexpectedBody,
    bool_of,
    chunks,
    decimal_of,
    items,
    obj,
    position_of,
    text_of,
    uuid_of,
)


def _reference(value: Any) -> Reference | None:
    if value is None:
        return None
    data = obj(value)
    return Reference(uuid_of(data, "id"), text_of(data, "code"), text_of(data, "name"))


def _filters(filters: CatalogFilters) -> dict[str, Any]:
    body: dict[str, Any] = {"status": filters.status}
    if filters.brand_ids:
        body["brand_ids"] = [str(i) for i in filters.brand_ids]
    if filters.category_ids:
        body["category_ids"] = [str(i) for i in filters.category_ids]
        body["include_descendants"] = filters.include_descendants
    for name in ("identifier", "product_type", "has_image"):
        value = getattr(filters, name)
        if value is not None:
            body[name] = value
    return body


class HTTPProductCatalog:
    def __init__(self, caller: TechnicalCaller) -> None:
        self._caller = caller

    def _bad(self, operation: str):
        return self._caller.client.unavailable(operation, "cuerpo_inesperado")

    async def summaries(self, ids: list[UUID]) -> dict[UUID, ProductSummary]:
        operation = "product_summaries"

        async def one(batch: list[UUID]) -> list[ProductSummary]:
            payload = await self._caller.json(
                operation, "POST", "/products/summaries/batch-lookup", json={"ids": [str(i) for i in batch]}
            )
            try:
                found = []
                for item in items(payload):
                    if not bool_of(item, "found"):
                        continue
                    found.append(
                        ProductSummary(
                            id=uuid_of(item, "id"),
                            canonical_name=text_of(item, "canonical_name"),
                            product_type=text_of(item, "product_type"),
                            status=text_of(item, "status"),
                            brand=_reference(item.get("brand")),
                            base_unit=_reference(item.get("base_unit")),
                            categories=tuple(
                                Category(uuid_of(c, "id"), text_of(c, "code"), text_of(c, "name"), bool_of(c, "is_primary"))
                                for c in items(item, "categories")
                            ),
                            identifiers=tuple(
                                Identifier(text_of(i, "type"), text_of(i, "value"), bool_of(i, "is_primary"),
                                           uuid_of(i, "global_product_presentation_id", optional=True))
                                for i in items(item, "identifiers")
                            ),
                        )
                    )
                return found
            except UnexpectedBody:
                raise self._bad(operation) from None

        results = await asyncio.gather(*(one(batch) for batch in chunks(list(dict.fromkeys(ids)))))
        return {summary.id: summary for batch in results for summary in batch}

    async def match_candidates(self, filters: CatalogFilters, candidate_ids: list[UUID]) -> list[UUID]:
        operation = "products_match_candidates"
        unique = list(dict.fromkeys(candidate_ids))
        if not unique:
            return []
        payload = await self._caller.json(
            operation, "POST", "/products/match", json={**_filters(filters), "candidate_ids": [str(i) for i in unique]}
        )
        try:
            values = obj(payload).get("ids")
            if not isinstance(values, list):
                raise UnexpectedBody("ids")
            return [UUID(str(value)) for value in values]
        except (UnexpectedBody, ValueError):
            raise self._bad(operation) from None

    async def match_page(self, filters: CatalogFilters, *, limit: int, after: dict | None = None):
        operation = "products_match_page"
        body = {**_filters(filters), "limit": limit, **({"after": after} if after else {})}
        payload = await self._caller.json(operation, "POST", "/products/match", json=body)
        try:
            page = [(uuid_of(item, "id"), position_of(item)) for item in items(payload)]
            return page, bool_of(obj(payload), "has_more")
        except UnexpectedBody:
            raise self._bad(operation) from None

    async def units(self, ids: list[UUID]) -> dict[UUID, Reference]:
        operation = "units_lookup"

        async def one(batch: list[UUID]) -> list[Reference]:
            payload = await self._caller.json(
                operation, "POST", "/units-of-measure/batch-lookup", json={"ids": [str(i) for i in batch]}
            )
            try:
                return [
                    Reference(uuid_of(item, "id"), text_of(item, "code"), text_of(item, "name"))
                    for item in items(payload)
                    if bool_of(item, "found")
                ]
            except UnexpectedBody:
                raise self._bad(operation) from None

        unique = list(dict.fromkeys(ids))
        if not unique:
            return {}
        results = await asyncio.gather(*(one(batch) for batch in chunks(unique)))
        return {unit.id: unit for batch in results for unit in batch}

    async def presentations(self, ids: list[UUID], *, include_images: bool = False) -> dict[UUID, PresentationInfo]:
        operation = "presentations_lookup"
        params = {"include_images": "true"} if include_images else None

        async def one(batch: list[UUID]) -> list[PresentationInfo]:
            payload = await self._caller.json(operation, "POST", "/presentations/batch-lookup",
                                              json={"ids": [str(i) for i in batch]}, params=params)
            try:
                return [
                    PresentationInfo(
                        id=uuid_of(item, "id"),
                        global_product_id=uuid_of(item, "global_product_id"),
                        code=text_of(item, "code"),
                        name=text_of(item, "name"),
                        status=text_of(item, "status"),
                        base_quantity=None if item.get("base_quantity") is None else decimal_of(item, "base_quantity"),
                        has_image=bool_of(item, "has_image"),
                        image_asset_id=uuid_of(item, "image_asset_id", optional=True),
                        image_url=text_of(item, "image_url", optional=True),
                        images=tuple(
                            PresentationImage(uuid_of(image, "asset_id"), text_of(image, "image_url", optional=True),
                                              bool_of(image, "is_primary"))
                            for image in items(item, "images")
                        ) if include_images else None,
                    )
                    for item in items(payload)
                    if bool_of(item, "found")
                ]
            except UnexpectedBody:
                raise self._bad(operation) from None

        unique = list(dict.fromkeys(ids))
        if not unique:
            return {}
        results = await asyncio.gather(*(one(batch) for batch in chunks(unique)))
        return {presentation.id: presentation for batch in results for presentation in batch}
