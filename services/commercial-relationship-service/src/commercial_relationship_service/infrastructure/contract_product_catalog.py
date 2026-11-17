"""Product Catalog leído de su vista de contrato (spec 025, T070; D27).

`ContractProductCatalogDirectory` implementa `ProductCatalogDirectory` igual que `HTTPProductCatalogDirectory`, que
hoy va con la identidad técnica propia (sin permiso del usuario):

| Método | Fuente |
|---|---|
| `get_product_base_unit` | `v1_products` (reemplaza `GET /products/{id}`) |
| `lookup_product`, `lookup_presentation` | siguen por API: `eligible_for_adoption` sale de la completitud de Product Catalog (FR-036) |
| `register_first_use` | sigue por API (escritura) |

- Sin fila → `None`, igual que el `404` de hoy. El GET no filtra por estado; la vista tampoco.
- `base_unit_id` vacío → la misma indisponibilidad que hoy produce un cuerpo inesperado.
- Cualquier error de base → `DependencyUnavailableError("product-catalog")`, el mismo `503` de hoy, con causa
  `contract:<causa>`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Engine

from commercial_relationship_service.application.exceptions import PRODUCT_CATALOG
from commercial_relationship_service.application.ports import GlobalPresentationRef, GlobalProductRef
from commercial_relationship_service.infrastructure.contract_support import ContractReader
from commercial_relationship_service.infrastructure.product_catalog_directory import HTTPProductCatalogDirectory

_PRODUCT = "SELECT base_unit_id FROM contract.v1_products WHERE id = :id"


class ContractProductCatalogDirectory:
    """Unidad base desde `v1_products`; elegibilidad y primer uso por el adaptador HTTP."""

    def __init__(self, *, engine: Engine, http: HTTPProductCatalogDirectory) -> None:
        self._reader = ContractReader(engine, PRODUCT_CATALOG)
        self._http = http

    def lookup_product(self, global_product_id: UUID) -> GlobalProductRef:
        return self._http.lookup_product(global_product_id)

    def register_first_use(
        self,
        global_product_id: UUID,
        global_product_presentation_id: UUID | None = None,
    ) -> None:
        self._http.register_first_use(global_product_id, global_product_presentation_id)

    def lookup_presentation(self, global_product_presentation_id: UUID) -> GlobalPresentationRef:
        return self._http.lookup_presentation(global_product_presentation_id)

    def get_product_base_unit(self, global_product_id: UUID) -> UUID | None:
        operation = "products_get"
        row = self._reader.one(operation, _PRODUCT, {"id": global_product_id})
        if row is None:
            return None
        return self._reader.required(operation, row, "base_unit_id")
