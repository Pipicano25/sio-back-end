"""Adaptador HTTP de Product Catalog (`contracts/product-catalog-dependency.md`).

Fase A (007): `products/batch-lookup` y `first-use`. Fase B (010, R-07):
`presentations/batch-lookup`, `GET products/{id}` (unidad base) y `first-use`
con presentación.

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
    GlobalPresentationNotEligibleError,
    GlobalPresentationNotFoundError,
    GlobalPresentationOfOtherProductError,
    GlobalProductNotEligibleError,
    GlobalProductNotFoundError,
)
from commercial_relationship_service.application.ports import (
    GlobalPresentationRef,
    GlobalProductRef,
)
from commercial_relationship_service.infrastructure.http_lookup import (
    HTTPDependencyClient,
    json_object,
)
from commercial_relationship_service.infrastructure.keycloak_token_client import (
    KeycloakTokenClient,
)

NOT_ELIGIBLE_CODE = "PRODUCT_CATALOG.NOT_ELIGIBLE_FOR_FIRST_USE"
OTHER_PRODUCT_CODE = "PRODUCT_CATALOG.PRESENTATION_OF_OTHER_PRODUCT"


class HTTPProductCatalogDirectory:
    """`batch-lookup`, producto, presentaciones y `first-use` con el token técnico del servicio."""

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

    def register_first_use(
        self,
        global_product_id: UUID,
        global_product_presentation_id: UUID | None = None,
    ) -> None:
        operation = "products_first_use"
        presentation = None if global_product_presentation_id is None else str(global_product_presentation_id)
        response = self._send(
            operation,
            "POST",
            f"/products/{global_product_id}/first-use",
            {"global_product_presentation_id": presentation},
        )

        if response.status_code == 200:
            return

        code = (json_object(response) or {}).get("code") if response.status_code == 422 else None

        if presentation is None:
            if response.status_code == 404:
                raise GlobalProductNotFoundError(field="global_product_id")

            if code == NOT_ELIGIBLE_CODE:
                raise GlobalProductNotEligibleError(field="global_product_id")

        else:
            field = "global_product_presentation_id"

            if response.status_code == 404:
                raise GlobalPresentationNotFoundError(field=field)

            if code == NOT_ELIGIBLE_CODE:
                raise GlobalPresentationNotEligibleError(field=field)

            if code == OTHER_PRODUCT_CODE:
                raise GlobalPresentationOfOtherProductError(field=field)

        raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

    def lookup_presentation(self, global_product_presentation_id: UUID) -> GlobalPresentationRef:
        operation = "presentations_batch_lookup"
        response = self._send(
            operation,
            "POST",
            "/presentations/batch-lookup",
            {"ids": [str(global_product_presentation_id)]},
        )

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        items = (json_object(response) or {}).get("items")

        if not isinstance(items, list):
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado")

        item = next(
            (
                entry
                for entry in items
                if isinstance(entry, dict) and entry.get("id") == str(global_product_presentation_id)
            ),
            None,
        )

        if item is None or not item.get("found"):
            return GlobalPresentationRef(found=False)

        try:
            owner = UUID(str(item.get("global_product_id")))
        except ValueError:
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado") from None

        return GlobalPresentationRef(
            found=True,
            global_product_id=owner,
            status=item.get("status"),
            eligible_for_adoption=bool(item.get("eligible_for_adoption")),
        )

    def get_product_base_unit(self, global_product_id: UUID) -> UUID | None:
        operation = "products_get"
        response = self._send(operation, "GET", f"/products/{global_product_id}", None)

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        try:
            return UUID(str((json_object(response) or {}).get("base_unit_id")))
        except ValueError:
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado") from None

    def _send(self, operation: str, method: str, path: str, body: dict | None) -> httpx.Response:
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
