"""Adaptador HTTP de Commercial Relationship (contratos 007 y 010; `contracts/dependencies.md`).

Identidad técnica de Purchase con el `read` de cada recurso y
`perm:commercial-relationship:platform:lookup` (lectura sin membresía). `404` o
`found = false` → `None` (el servicio de aplicación decide `422`); `5xx`, `401` tras
renovar, `403`, red, tiempo agotado o cuerpo inesperado → `503 commercial-relationship`.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import httpx

from purchase_service.application.exceptions import COMMERCIAL_RELATIONSHIP
from purchase_service.application.ports import (
    CompanyPresentationInfo,
    CompanyProductInfo,
    PaymentConditionInfo,
    SupplierInfo,
    SupplierProductInfo,
)
from purchase_service.infrastructure.http_client import (
    HTTPDependencyClient,
    TechnicalCaller,
    UnexpectedBody,
    bool_field,
    date_field,
    json_object,
    decimal_field,
    int_field,
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

    def get_supplier(self, supplier_id: UUID) -> SupplierInfo | None:
        body = self._caller.get_object("company_supplier", f"/company-suppliers/{supplier_id}")
        if body is None:
            return None
        try:
            return SupplierInfo(
                id=supplier_id,
                company_id=uuid_field(body, "company_id"),
                organization_identity_id=uuid_field(body, "organization_identity_id"),
                display_name=text_field(body, "display_name"),
                status=text_field(body, "status"),
            )
        except UnexpectedBody as exc:
            raise self._bad("company_supplier", exc) from None

    def get_payment_condition(self, condition_id: UUID) -> PaymentConditionInfo | None:
        body = self._caller.get_object("supplier_payment_condition", f"/supplier-payment-conditions/{condition_id}")
        if body is None:
            return None
        try:
            return PaymentConditionInfo(
                id=condition_id,
                company_id=uuid_field(body, "company_id"),
                company_supplier_id=uuid_field(body, "company_supplier_id"),
                payment_condition_type_id=uuid_field(body, "payment_condition_type_id"),
                currency_code=text_field(body, "currency_code"),
                payment_terms_days=int_field(body, "payment_terms_days"),
                valid_from=date_field(body, "valid_from", optional=True),
                valid_to=date_field(body, "valid_to", optional=True),
                status=text_field(body, "status"),
            )
        except UnexpectedBody as exc:
            raise self._bad("supplier_payment_condition", exc) from None

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
                        is_purchasable=bool_field(item, "is_purchasable"),
                        inventory_control_enabled=bool_field(item, "inventory_control_enabled"),
                        status=text_field(item, "status"),
                        # Spec 021 (FR-021-08): campo aditivo; ausente o nulo = sin configurar.
                        purchase_tax_percentage=decimal_field(item, "purchase_tax_percentage", optional=True),
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
                        is_purchasable=bool_field(item, "is_purchasable"),
                        status=text_field(item, "status"),
                    )
            except UnexpectedBody as exc:
                raise self._bad("company_product_presentations_batch", exc) from None
        return result

    def lookup_pricing_coverage(self, company_id: UUID, currency_code: str, ids: Sequence[UUID]) -> dict[UUID, bool]:
        """Cobertura de políticas (spec 021, FR-021-35; contrato CR §3b), de a 100 presentaciones.

        Solo se aceptan las presentaciones pedidas; cualquier respuesta distinta de `200` con `items` válidos es un
        error técnico (`503`): Purchase nunca asume cobertura.
        """
        result: dict[UUID, bool] = {}
        distinct = list(dict.fromkeys(ids))
        operation = "pricing_policy_coverage"
        for start in range(0, len(distinct), BATCH_LIMIT):
            chunk = distinct[start : start + BATCH_LIMIT]
            response = self._caller.send(
                operation,
                "POST",
                f"/companies/{company_id}/pricing-policies/coverage",
                json={"currency_code": currency_code, "company_product_presentation_ids": [str(value) for value in chunk]},
            )
            if response.status_code != 200:
                raise self._caller.client.unavailable(operation, outcome=f"estado={response.status_code}")
            body = json_object(response)
            items = body.get("items") if body else None
            if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
                raise self._caller.client.unavailable(operation, outcome="cuerpo_inesperado")
            requested = set(chunk)
            try:
                for item in items:
                    presentation_id = uuid_field(item, "company_product_presentation_id")
                    if presentation_id in requested:
                        result[presentation_id] = bool_field(item, "found") and bool_field(item, "covered")
            except UnexpectedBody as exc:
                raise self._bad(operation, exc) from None
            if requested - set(result):  # toda presentación pedida debe tener respuesta
                raise self._caller.client.unavailable(operation, outcome="cuerpo_incompleto")
        return result

    def get_supplier_product(self, supplier_product_id: UUID) -> SupplierProductInfo | None:
        body = self._caller.get_object("supplier_product", f"/supplier-products/{supplier_product_id}")
        if body is None:
            return None
        try:
            return SupplierProductInfo(
                id=supplier_product_id,
                company_id=uuid_field(body, "company_id"),
                company_supplier_id=uuid_field(body, "company_supplier_id"),
                company_product_id=uuid_field(body, "company_product_id"),
                company_product_presentation_id=uuid_field(body, "company_product_presentation_id", optional=True),
                expected_supplier_lead_time_hours=decimal_field(
                    body, "expected_supplier_lead_time_hours", optional=True
                ),
                status=text_field(body, "status"),
            )
        except UnexpectedBody as exc:
            raise self._bad("supplier_product", exc) from None
