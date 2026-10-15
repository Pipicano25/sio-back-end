"""Adaptador HTTP de Payment Reference (contrato 008; spec 020).

`GET {BASE}/global-payment-methods/{id}` con la identidad técnica de Sales
(`perm:payment-reference:global_payment_methods:read`), con `{BASE}` **sin** `/api/v1` (brecha
diferida del proveedor, igual que en Purchase). `200` → método, `404` → `None` (inexistente, `422`);
cualquier otro → `503 payment-reference`. El medio de pago es una referencia declarativa: Sales no
registra ni comprueba pagos.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from sales_service.application.exceptions import PAYMENT_REFERENCE
from sales_service.application.ports import PaymentMethodInfo
from sales_service.infrastructure.http_client import HTTPDependencyClient, TechnicalCaller, UnexpectedBody, text_field


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
