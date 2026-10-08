"""Adaptador HTTP de Commercial Relationship (contratos 007 y 010; `contracts/dependencies.md`).

Identidad técnica de Sales con el `read` de cada recurso y
`perm:commercial-relationship:platform:lookup` (lectura sin membresía). `404` o
`found = false` → `None` (el servicio de aplicación decide `422`); `5xx`, `401` tras
renovar, `403`, red, tiempo agotado o cuerpo inesperado → `503 commercial-relationship`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

import httpx

from sales_service.application.exceptions import COMMERCIAL_RELATIONSHIP
from sales_service.application.ports import (
    CompanyPresentationInfo,
    CompanyProductInfo,
    CustomerInfo,
    PriceListInfo,
    PriceRequestLine,
    ResolvedPrice,
)
from sales_service.infrastructure.http_client import (
    HTTPDependencyClient,
    TechnicalCaller,
    UnexpectedBody,
    bool_field,
    decimal_field,
    json_object,
    text_field,
    uuid_field,
)

BATCH_LIMIT = 100


class HTTPCommercialDirectory:
    def __init__(
        self, *, base_url: str, timeout_seconds: float, tokens, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._caller = TechnicalCaller(
            HTTPDependencyClient(
                provider=COMMERCIAL_RELATIONSHIP,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                unavailable_cause="commercial_relationship_unreachable",
                transport=transport,
            ),
            tokens,
        )

    def _bad(self, operation: str, exc: UnexpectedBody):
        return self._caller.client.unavailable(operation, outcome=f"cuerpo_inesperado:{exc}")

    def get_customer(self, customer_id: UUID) -> CustomerInfo | None:
        body = self._caller.get_object("company_customer", f"/company-customers/{customer_id}")
        if body is None:
            return None
        try:
            return CustomerInfo(
                id=customer_id,
                company_id=uuid_field(body, "company_id"),
                customer_kind=text_field(body, "customer_kind"),
                person_identity_id=uuid_field(body, "person_identity_id", optional=True),
                organization_identity_id=uuid_field(body, "organization_identity_id", optional=True),
                display_name=text_field(body, "display_name"),
                status=text_field(body, "status"),
            )
        except UnexpectedBody as exc:
            raise self._bad("company_customer", exc) from None

    def lookup_products(self, ids: Sequence[UUID]) -> dict[UUID, CompanyProductInfo]:
        result: dict[UUID, CompanyProductInfo] = {}
        distinct = list(dict.fromkeys(ids))
        for start in range(0, len(distinct), BATCH_LIMIT):
            items = self._caller.post_items(
                "company_products_batch",
                "/company-products/batch-lookup",
                [str(value) for value in distinct[start : start + BATCH_LIMIT]],
            )
            try:
                for item in items:
                    if item.get("found") is not True:
                        continue
                    product_id = uuid_field(item, "id")
                    result[product_id] = CompanyProductInfo(
                        id=product_id,
                        company_id=uuid_field(item, "company_id"),
                        global_product_id=uuid_field(item, "global_product_id"),
                        internal_code=text_field(item, "internal_code"),
                        display_name=text_field(item, "display_name"),
                        is_sellable=bool_field(item, "is_sellable"),
                        inventory_control_enabled=bool_field(item, "inventory_control_enabled"),
                        status=text_field(item, "status"),
                    )
            except UnexpectedBody as exc:
                raise self._bad("company_products_batch", exc) from None
        return result

    def lookup_presentations(self, ids: Sequence[UUID]) -> dict[UUID, CompanyPresentationInfo]:
        result: dict[UUID, CompanyPresentationInfo] = {}
        distinct = list(dict.fromkeys(ids))
        for start in range(0, len(distinct), BATCH_LIMIT):
            items = self._caller.post_items(
                "company_product_presentations_batch",
                "/company-product-presentations/batch-lookup",
                [str(value) for value in distinct[start : start + BATCH_LIMIT]],
            )
            try:
                for item in items:
                    if item.get("found") is not True:
                        continue
                    presentation_id = uuid_field(item, "id")
                    result[presentation_id] = CompanyPresentationInfo(
                        id=presentation_id,
                        company_id=uuid_field(item, "company_id"),
                        company_product_id=uuid_field(item, "company_product_id"),
                        global_product_presentation_id=uuid_field(item, "global_product_presentation_id"),
                        is_sellable=bool_field(item, "is_sellable"),
                        status=text_field(item, "status"),
                    )
            except UnexpectedBody as exc:
                raise self._bad("company_product_presentations_batch", exc) from None
        return result

    def resolve_prices(
        self, company_id: UUID, lines: Sequence[PriceRequestLine], at: datetime
    ) -> dict[str, ResolvedPrice]:
        """Precio aplicable por línea (contrato 010 §6); un solo `POST` por cada 100 líneas."""
        operation = "applicable_prices"
        result: dict[str, ResolvedPrice] = {}
        for start in range(0, len(lines), BATCH_LIMIT):
            chunk = lines[start : start + BATCH_LIMIT]
            body_lines = []
            for line in chunk:
                entry: dict[str, str] = {"line_id": line.line_id, "company_product_id": str(line.company_product_id)}
                if line.company_product_presentation_id is not None:
                    entry["company_product_presentation_id"] = str(line.company_product_presentation_id)
                if line.price_list_id is not None:
                    entry["price_list_id"] = str(line.price_list_id)
                body_lines.append(entry)
            response = self._caller.send(
                operation,
                "POST",
                f"/companies/{company_id}/applicable-prices/resolve",
                json={"at": at.isoformat(), "lines": body_lines},
            )
            if response.status_code != 200:
                raise self._caller.client.unavailable(operation, outcome=f"estado={response.status_code}")
            body = json_object(response)
            items = body.get("items") if body else None
            if not isinstance(items, list) or len(items) != len(chunk):
                raise self._caller.client.unavailable(operation, outcome="cuerpo_inesperado")
            try:
                for item in items:
                    if not isinstance(item, dict):
                        raise UnexpectedBody("items")
                    line_id = text_field(item, "line_id")
                    result[line_id] = ResolvedPrice(
                        line_id=line_id,
                        found=bool_field(item, "found"),
                        resolution=text_field(item, "resolution"),
                        basis=text_field(item, "basis", optional=True),
                        unit_price=decimal_field(item, "unit_price", optional=True),
                        currency_code=text_field(item, "currency_code", optional=True),
                        price_list_id=uuid_field(item, "price_list_id", optional=True),
                        price_list_item_id=uuid_field(item, "price_list_item_id", optional=True),
                    )
            except UnexpectedBody as exc:
                raise self._bad(operation, exc) from None
        return result

    def get_price_list(self, price_list_id: UUID) -> PriceListInfo | None:
        body = self._caller.get_object("price_list", f"/price-lists/{price_list_id}")
        if body is None:
            return None
        try:
            return PriceListInfo(
                id=price_list_id,
                company_id=uuid_field(body, "company_id"),
                status=text_field(body, "status"),
            )
        except UnexpectedBody as exc:
            raise self._bad("price_list", exc) from None
