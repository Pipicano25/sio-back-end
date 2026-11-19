"""Adaptador HTTP de las lecturas por lotes de Product Catalog para la adopción masiva (spec 027, R4).

Rutas consumidas (todas con `perm:product-catalog:products:read` y la identidad técnica propia, R-05):

- `POST /products/match` (modo conductor, Historia 3);
- `POST /products/batch-lookup`;
- `POST /products/summaries/batch-lookup`;
- `GET /products/{id}/presentations?status=ACTIVE`;
- `POST /presentations/batch-lookup`.

Mismo `timeout` y misma renovación del token que `product_catalog_directory.py`: ante `401` se renueva y se repite
una vez; un segundo `401` o un `403` se exponen como `DependencyUnavailableError`. Cualquier estado inesperado o
cuerpo mal formado también es `DependencyUnavailableError` (la adopción lo informa como `DEPENDENCY_UNAVAILABLE`).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx

from commercial_relationship_service.application.exceptions import (
    PRODUCT_CATALOG,
    PRODUCT_CATALOG_ACCESS_DENIED,
    PRODUCT_CATALOG_UNREACHABLE,
)
from commercial_relationship_service.application.ports import (
    CatalogIdentifier,
    CatalogMatchPage,
    CatalogPresentation,
    CatalogPresentationLookup,
    CatalogProductLookup,
    CatalogProductSummary,
    GlobalPresentationRef,
    GlobalProductRef,
)
from commercial_relationship_service.infrastructure.http_lookup import HTTPDependencyClient, json_object
from commercial_relationship_service.infrastructure.keycloak_token_client import KeycloakTokenClient


class _UnexpectedBody(ValueError):
    """Cuerpo de Product Catalog que no cumple su contrato."""


def _uuid(value: Any) -> UUID:
    try:
        return UUID(str(value))
    except ValueError:
        raise _UnexpectedBody from None


def _optional_uuid(value: Any) -> UUID | None:
    return None if value is None else _uuid(value)


def _entries(body: dict | None, key: str = "items") -> list[dict]:
    items = (body or {}).get(key)
    if not isinstance(items, list) or not all(isinstance(entry, dict) for entry in items):
        raise _UnexpectedBody
    return items


class HTTPProductCatalogBulkDirectory:
    """Implementa `ProductCatalogBulkDirectory` contra la API HTTP de Product Catalog."""

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

    # ------------------------------------------------------------- lecturas

    def match_products(
        self,
        *,
        category_ids: list[UUID],
        brand_ids: list[UUID],
        include_descendants: bool,
        after: dict | None,
        limit: int,
    ) -> CatalogMatchPage:
        body = {
            "category_ids": [str(item) for item in category_ids],
            "brand_ids": [str(item) for item in brand_ids],
            "include_descendants": include_descendants,
            "status": "ACTIVE",
            "after": after,
            "limit": limit,
        }

        def parse(payload: dict | None) -> CatalogMatchPage:
            items = _entries(payload)
            ids = [_uuid(entry.get("id")) for entry in items]
            position = items[-1].get("position") if items else after
            has_more = (payload or {}).get("has_more")
            if not isinstance(has_more, bool):
                raise _UnexpectedBody
            return CatalogMatchPage(ids=ids, after=position, has_more=has_more)

        return self._call("products_match", "POST", "/products/match", parse, json=body)

    def lookup_products(self, ids: list[UUID]) -> list[CatalogProductLookup]:
        def parse(payload: dict | None) -> list[CatalogProductLookup]:
            found = {}
            for entry in _entries(payload):
                ref = (
                    GlobalProductRef(
                        found=True,
                        status=entry.get("status"),
                        eligible_for_adoption=bool(entry.get("eligible_for_adoption")),
                    )
                    if entry.get("found")
                    else GlobalProductRef(found=False)
                )
                found[_uuid(entry.get("id"))] = ref
            return [CatalogProductLookup(id=item, ref=found.get(item, GlobalProductRef(found=False))) for item in ids]

        return self._call(
            "products_batch_lookup", "POST", "/products/batch-lookup", parse, json={"ids": [str(item) for item in ids]}
        )

    def product_summaries(self, ids: list[UUID]) -> dict[UUID, CatalogProductSummary]:
        def parse(payload: dict | None) -> dict[UUID, CatalogProductSummary]:
            summaries = {}
            for entry in _entries(payload):
                product_id = _uuid(entry.get("id"))
                if not entry.get("found"):
                    summaries[product_id] = CatalogProductSummary(id=product_id, found=False)
                    continue
                identifiers = tuple(
                    CatalogIdentifier(
                        type=str(identifier.get("type")),
                        value=str(identifier.get("value")),
                        is_primary=bool(identifier.get("is_primary")),
                        global_product_presentation_id=_optional_uuid(identifier.get("global_product_presentation_id")),
                    )
                    for identifier in _entries(entry, "identifiers")
                )
                summaries[product_id] = CatalogProductSummary(
                    id=product_id,
                    found=True,
                    canonical_name=entry.get("canonical_name"),
                    status=entry.get("status"),
                    identifiers=identifiers,
                )
            return {item: summaries.get(item, CatalogProductSummary(id=item, found=False)) for item in ids}

        return self._call(
            "products_summaries_batch_lookup",
            "POST",
            "/products/summaries/batch-lookup",
            parse,
            json={"ids": [str(item) for item in ids]},
        )

    def product_presentations(self, global_product_id: UUID) -> list[CatalogPresentation]:
        def parse(payload: Any) -> list[CatalogPresentation]:
            if not isinstance(payload, list) or not all(isinstance(entry, dict) for entry in payload):
                raise _UnexpectedBody
            return [
                CatalogPresentation(
                    id=_uuid(entry.get("id")),
                    global_product_id=_uuid(entry.get("global_product_id")),
                    status=str(entry.get("status")),
                    is_base=bool(entry.get("is_base")),
                    eligible_for_adoption=bool(entry.get("eligible_for_adoption")),
                )
                for entry in payload
            ]

        return self._call(
            "products_presentations_list",
            "GET",
            f"/products/{global_product_id}/presentations",
            parse,
            params={"status": "ACTIVE"},
            not_found=list,
            raw=True,
        )

    def lookup_presentations(self, ids: list[UUID]) -> list[CatalogPresentationLookup]:
        def parse(payload: dict | None) -> list[CatalogPresentationLookup]:
            found = {}
            for entry in _entries(payload):
                ref = (
                    GlobalPresentationRef(
                        found=True,
                        global_product_id=_uuid(entry.get("global_product_id")),
                        status=entry.get("status"),
                        eligible_for_adoption=bool(entry.get("eligible_for_adoption")),
                    )
                    if entry.get("found")
                    else GlobalPresentationRef(found=False)
                )
                found[_uuid(entry.get("id"))] = ref
            return [
                CatalogPresentationLookup(id=item, ref=found.get(item, GlobalPresentationRef(found=False)))
                for item in ids
            ]

        return self._call(
            "presentations_batch_lookup",
            "POST",
            "/presentations/batch-lookup",
            parse,
            json={"ids": [str(item) for item in ids]},
        )

    # -------------------------------------------------------------- internos

    def _call(self, operation, method, path, parse, *, json=None, params=None, not_found=None, raw=False):
        response = self._send(operation, method, path, json=json, params=params)

        if response.status_code == 404 and not_found is not None:
            return not_found()

        if response.status_code != 200:
            raise self._client.unavailable(operation, outcome=f"estado={response.status_code}")

        if raw:
            try:
                payload = response.json()
            except ValueError:
                raise self._client.unavailable(operation, outcome="cuerpo_inesperado") from None
        else:
            payload = json_object(response)

        try:
            return parse(payload)
        except _UnexpectedBody:
            raise self._client.unavailable(operation, outcome="cuerpo_inesperado") from None

    def _send(self, operation: str, method: str, path: str, *, json: Any, params: dict | None) -> httpx.Response:
        response = self._client.send(operation, method, path, authorization=self._bearer(), json=json, params=params)

        if response.status_code == 401:
            # Token caducado o revocado: se renueva y se repite una sola vez (R-05).
            self._tokens.invalidate()
            response = self._client.send(
                operation, method, path, authorization=self._bearer(), json=json, params=params
            )

        if response.status_code in {401, 403}:
            raise self._client.unavailable(
                operation, cause=PRODUCT_CATALOG_ACCESS_DENIED, outcome=f"estado={response.status_code}"
            )

        return response

    def _bearer(self) -> str:
        return f"Bearer {self._tokens.get_token()}"
