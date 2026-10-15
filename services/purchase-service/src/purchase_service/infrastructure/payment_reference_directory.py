"""Adaptador HTTP de Payment Reference (contrato 008; `contracts/dependencies.md`; spec 020).

`GET {BASE}/global-payment-condition-types/{id}` y `GET {BASE}/global-payment-methods/{id}`
(spec 020), con `{BASE}` **sin** `/api/v1` (brecha diferida del proveedor). Se distingue por código HTTP (FR-022 (008)): `200` → tipo,
`404` → `None`, cualquier otro → `503 payment-reference`.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from purchase_service.application.exceptions import PAYMENT_REFERENCE
from purchase_service.application.ports import PaymentConditionTypeInfo, PaymentMethodInfo
from purchase_service.infrastructure.http_client import HTTPDependencyClient, TechnicalCaller, UnexpectedBody, text_field


class HTTPPaymentReferenceDirectory:
    def __init__(
        self, *, base_url: str, timeout_seconds: float, tokens, transport: httpx.BaseTransport | None = None
    ) -> None:
        self._caller = TechnicalCaller(
            HTTPDependencyClient(
                provider=PAYMENT_REFERENCE,
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                unavailable_cause="payment_reference_unreachable",
                transport=transport,
            ),
            tokens,
        )

    def get_condition_type(self, type_id: UUID) -> PaymentConditionTypeInfo | None:
        body = self._caller.get_object("payment_condition_type", f"/global-payment-condition-types/{type_id}")
        if body is None:
            return None
        try:
            return PaymentConditionTypeInfo(id=type_id, code=text_field(body, "code"), status=text_field(body, "status"))
        except UnexpectedBody as exc:
            raise self._caller.client.unavailable(
                "payment_condition_type", outcome=f"cuerpo_inesperado:{exc}"
            ) from None

    def get_payment_method(self, method_id: UUID) -> PaymentMethodInfo | None:
        body = self._caller.get_object("payment_method", f"/global-payment-methods/{method_id}")
        if body is None:
            return None
        try:
            return PaymentMethodInfo(
                id=method_id,
                code=text_field(body, "code"),
                name=text_field(body, "name"),
                status=text_field(body, "status"),
            )
        except UnexpectedBody as exc:
            raise self._caller.client.unavailable("payment_method", outcome=f"cuerpo_inesperado:{exc}") from None
