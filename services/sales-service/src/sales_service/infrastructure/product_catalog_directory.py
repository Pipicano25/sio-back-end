"""Adaptador HTTP de Product Catalog (contrato 002; `contracts/dependencies.md`).

Identidad técnica con `perm:product-catalog:products:read` y
`perm:product-catalog:units-of-measure:read`. Lee la presentación global (código,
nombre, `base_quantity`), la unidad base del producto global y el código de la unidad.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from sales_service.application.exceptions import PRODUCT_CATALOG
from sales_service.application.ports import GlobalPresentationInfo, GlobalProductInfo, UnitInfo
from sales_service.infrastructure.http_client import (
    HTTPDependencyClient,
    TechnicalCaller,
    UnexpectedBody,
    decimal_field,
    text_field,
    uuid_field,
)


class HTTPCatalogDirectory:
    def __init__(
        self, *, base_url: str, timeout_seconds: float, tokens, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._caller = TechnicalCaller(
            HTTPDependencyClient(
                provider=PRODUCT_CATALOG,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                unavailable_cause="product_catalog_unreachable",
                transport=transport,
            ),
            tokens,
        )

    def _bad(self, operation: str, exc: UnexpectedBody):
        return self._caller.client.unavailable(operation, outcome=f"cuerpo_inesperado:{exc}")

    def get_presentation(self, presentation_id: UUID) -> GlobalPresentationInfo | None:
        body = self._caller.get_object("presentation", f"/presentations/{presentation_id}")
        if body is None:
            return None
        try:
            return GlobalPresentationInfo(
                id=presentation_id,
                code=text_field(body, "code"),
                name=text_field(body, "name"),
                base_quantity=decimal_field(body, "base_quantity"),
            )
        except UnexpectedBody as exc:
            raise self._bad("presentation", exc) from None

    def get_product(self, product_id: UUID) -> GlobalProductInfo | None:
        body = self._caller.get_object("product", f"/products/{product_id}")
        if body is None:
            return None
        try:
            return GlobalProductInfo(id=product_id, base_unit_id=uuid_field(body, "base_unit_id"))
        except UnexpectedBody as exc:
            raise self._bad("product", exc) from None

    def get_unit(self, unit_id: UUID) -> UnitInfo | None:
        body = self._caller.get_object("unit_of_measure", f"/units-of-measure/{unit_id}")
        if body is None:
            return None
        try:
            return UnitInfo(id=unit_id, code=text_field(body, "code"))
        except UnexpectedBody as exc:
            raise self._bad("unit_of_measure", exc) from None
