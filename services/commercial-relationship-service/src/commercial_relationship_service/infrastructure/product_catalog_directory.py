"""Adaptador HTTP de Product Catalog (`contracts/product-catalog-dependency.md`).

Usa la identidad técnica propia (`client_credentials`, R-05). Ante `401` renueva
el token y repite la llamada **una** vez; un segundo `401` o un `403` son un
error de configuración del cliente técnico y se exponen como `503`.
"""

from __future__ import annotations

from uuid import UUID

import httpx

from commercial_relationship_service.application.exceptions import (
    PRODUCT_CATALOG,
    PRODUCT_CATALOG_ACCESS_DENIED,
    PRODUCT_CATALOG_UNREACHABLE,
    GlobalProductNotEligibleError,
    GlobalProductNotFoundError,
)
from commercial_relationship_service.application.ports import GlobalProductRef
from commercial_relationship_service.infrastructure.http_lookup import (
    HTTPDependencyClient,
    json_object,
)
from commercial_relationship_service.infrastructure.keycloak_token_client import (
    KeycloakTokenClient,
)

NOT_ELIGIBLE_CODE = "PRODUCT_CATALOG.NOT_ELIGIBLE_FOR_FIRST_USE"


class HTTPProductCatalogDirectory:
    """`batch-lookup` y `first-use` con el token técnico del servicio."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        token_client: KeycloakTokenClient,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = HTTPDependencyClient(
            provider=PRODUCT_CATALOG,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            unavailable_cause=PRODUCT_CATALOG_UNREACHABLE,
            transport=transport,
        )
        self._tokens = token_client

    def lookup_product(self, global_product_id: UUID) -> GlobalProductRef:
        operation = "products_batch_lookup"
        response = self._send(
            operation, "POST", "/products/batch-lookup", {"ids": [str(global_product_id)]}
        )

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        body = json_object(response) or {}
        items = body.get("items")

        if not isinstance(items, list):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        item = next(
            (entry for entry in items if isinstance(entry, dict) and entry.get("id") == str(global_product_id)),
            None,
        )

        if item is None or not item.get("found"):
            return GlobalProductRef(found=False)

        return GlobalProductRef(
            found=True,
            status=item.get("status"),
            eligible_for_adoption=bool(item.get("eligible_for_adoption")),
        )

    def register_first_use(self, global_product_id: UUID) -> None:
        operation = "products_first_use"
        response = self._send(
            operation,
            "POST",
            f"/products/{global_product_id}/first-use",
            {"global_product_presentation_id": None},
        )

        if response.status_code == 200:
            return

        if response.status_code == 404:
            raise GlobalProductNotFoundError(field="global_product_id")

        if response.status_code == 422 and (json_object(response) or {}).get("code") == NOT_ELIGIBLE_CODE:
            raise GlobalProductNotEligibleError(field="global_product_id")

        raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

    def _send(self, operation: str, method: str, path: str, body: dict) -> httpx.Response:
        response = self._client.send(
            operation, method, path, authorization=self._bearer(), json=body
        )

        if response.status_code == 401:
            # Token caducado o revocado: se renueva y se repite una sola vez (R-05).
            self._tokens.invalidate()
            response = self._client.send(
                operation, method, path, authorization=self._bearer(), json=body
            )

        if response.status_code in {401, 403}:
            raise self._client.unavailable(
                operation,
                cause=PRODUCT_CATALOG_ACCESS_DENIED,
                outcome=f"estado={response.status_code}",
            )

        return response

    def _bearer(self) -> str:
        return f"Bearer {self._tokens.get_token()}"
