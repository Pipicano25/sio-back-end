"""Adaptador HTTP de la entrega de solicitudes de precio a Commercial Relationship (spec 021, EXC-001).

`POST /companies/{company_id}/automatic-price-update-requests` con la identidad técnica de Purchase
(`client_credentials`, D5). No lanza excepciones por fallos de CR: devuelve el resultado para que el worker decida si
reintenta (Principio XV: tiempo de espera y manejo de indisponibilidad propios).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from purchase_service.application.exceptions import DependencyUnavailableError
from purchase_service.application.ports import DeliveryResult
from purchase_service.infrastructure.http_client import HTTPDependencyClient, TechnicalCaller, json_object

COMMERCIAL_RELATIONSHIP = "commercial-relationship"
ACCEPTED, REJECTED, RETRY = "ACCEPTED", "REJECTED", "RETRY"


class HTTPCommercialPricingGateway:
    def __init__(self, *, base_url: str, timeout_seconds: float, tokens, transport: httpx.BaseTransport | None = None) -> None:
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

    def submit(self, company_id: UUID, payload: dict[str, Any]) -> DeliveryResult:
        try:
            response = self._caller.send(
                "automatic_price_update_request", "POST", f"/companies/{company_id}/automatic-price-update-requests",
                json=payload,
            )
        except DependencyUnavailableError:
            return DeliveryResult(RETRY, "COMMERCIAL_RELATIONSHIP_UNAVAILABLE")
        if response.status_code == 202:
            return DeliveryResult(ACCEPTED)
        body = json_object(response) or {}
        code = str(body.get("code") or f"HTTP_{response.status_code}").removeprefix("COMMERCIAL_RELATIONSHIP.")
        if response.status_code == 409:
            return DeliveryResult(REJECTED, code)
        return DeliveryResult(RETRY, code)
