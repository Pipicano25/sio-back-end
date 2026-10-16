"""Adaptador HTTP de Product Catalog (contrato 002; `contracts/dependencies.md`).

Identidad técnica con `perm:product-catalog:products:read` y
`perm:product-catalog:units-of-measure:read`. Lee la presentación global (código,
nombre, `base_quantity`), la unidad base del producto global y el código de la unidad.

Spec 021 (H-2): las presentaciones de una compra se leen con `POST /presentations/batch-lookup` (hasta 100 por
llamada) en lugar de una consulta por presentación.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import httpx

from purchase_service.application.exceptions import PRODUCT_CATALOG
from purchase_service.application.ports import GlobalPresentationInfo, GlobalProductInfo, UnitInfo
from purchase_service.infrastructure.http_client import (
    HTTPDependencyClient,
    TechnicalCaller,
    UnexpectedBody,
    decimal_field,
    text_field,
    uuid_field,
)

BATCH_LIMIT = 100  # máximo de `batch-lookup` en Product Catalog


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

    def lookup_presentations(self, ids: Sequence[UUID]) -> dict[UUID, GlobalPresentationInfo]:
        """Presentaciones globales por lotes; las no encontradas no aparecen (equivale a `get_presentation`).

        Solo se aceptan los identificadores pedidos. Si Product Catalog aún no devuelve `code` y `name` en
        `batch-lookup` (versión anterior durante un despliegue), esa presentación se lee con la consulta individual.
        """
        result: dict[UUID, GlobalPresentationInfo] = {}
        incomplete: list[UUID] = []
        distinct = list(dict.fromkeys(ids))
        for start in range(0, len(distinct), BATCH_LIMIT):
            chunk = distinct[start : start + BATCH_LIMIT]
            items = self._caller.post_items(
                "presentations_batch", "/presentations/batch-lookup", [str(value) for value in chunk]
            )
            requested = set(chunk)
            try:
                for item in items:
                    if item.get("found") is not True:
                        continue
                    presentation_id = uuid_field(item, "id")
                    if presentation_id not in requested:
                        continue
                    if item.get("code") is None or item.get("name") is None:
                        incomplete.append(presentation_id)
                        continue
                    result[presentation_id] = GlobalPresentationInfo(
                        id=presentation_id,
                        code=text_field(item, "code"),
                        name=text_field(item, "name"),
                        base_quantity=decimal_field(item, "base_quantity"),
                    )
            except UnexpectedBody as exc:
                raise self._bad("presentations_batch", exc) from None
        for presentation_id in incomplete:
            info = self.get_presentation(presentation_id)
            if info is not None:
                result[presentation_id] = info
        return result

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
