"""Adaptador HTTP de Commercial Relationship (`contracts/dependencies.md`, R-07).

`POST {CR}/company-products/batch-lookup` con la identidad técnica de Inventory
(`company_products:read` + `platform:lookup`), una llamada por operación con los
productos distintos (≤ 100). `found=false` → ausente del resultado.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

import httpx

from inventory_service.application.exceptions import COMMERCIAL_RELATIONSHIP
from inventory_service.application.ports import CompanyProductInfo, TokenProvider
from inventory_service.infrastructure.http_lookup import HTTPDependencyClient, json_object
from inventory_service.infrastructure.operational_context_directory import TechnicalCaller, _uuid


class HTTPCompanyProductDirectory:
    """Productos empresariales por lotes con la identidad técnica de Inventory."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        tokens: TokenProvider,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = HTTPDependencyClient(
            provider=COMMERCIAL_RELATIONSHIP,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            unavailable_cause="commercial_relationship_unreachable",
            transport=transport,
        )
        self._caller = TechnicalCaller(self._client, tokens)

    def lookup(self, product_ids: Iterable[UUID]) -> dict[UUID, CompanyProductInfo]:
        operation = "batch_lookup"
        ids = list(dict.fromkeys(product_ids))

        if not ids:
            return {}

        response = self._caller.send(
            operation, "POST", "/company-products/batch-lookup", json={"ids": [str(item) for item in ids]}
        )

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response)
        items = body.get("items") if body else None

        if not isinstance(items, list):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        found: dict[UUID, CompanyProductInfo] = {}

        for item in items:
            info = self._parse(item)
            if info is not None:
                found[info.id] = info

        return found

    def _parse(self, item: Any) -> CompanyProductInfo | None:
        if not isinstance(item, dict) or not isinstance(item.get("found"), bool):
            raise self._client.unavailable("batch_lookup", outcome="cuerpo_inesperado")

        if not item["found"]:
            return None

        product_id = _uuid(item.get("id"))
        company_id = _uuid(item.get("company_id"))
        status = item.get("status")
        control = item.get("inventory_control_enabled")

        if product_id is None or company_id is None or not isinstance(status, str) or not isinstance(control, bool):
            raise self._client.unavailable("batch_lookup", outcome="cuerpo_inesperado")

        return CompanyProductInfo(
            id=product_id, company_id=company_id, status=status, inventory_control_enabled=control
        )
