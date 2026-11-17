"""Unidad base de los productos globales leída de las vistas de contrato de Product Catalog (spec 025, T074; D27).

Mismo puerto que `HTTPProductCatalog`: `contract.v1_products` con `contract.v1_units_of_measure` reemplazan a
`POST /products/summaries/batch-lookup` (solo se usaba `base_unit`):

1. hoy la llamada va con el token del usuario y Product Catalog exige `perm:product-catalog:products:read`; sin él
   se lanza `OwnerForbiddenError`, el mismo error que hoy produce su `403` (FR-037). Como hoy, sin ids no se
   comprueba nada ni se consulta;
2. ids únicos en el orden recibido, por lotes de 100; cada id pedido queda en el resultado: producto inexistente
   (`found=false`) o sin unidad → `None`; si no, `UnitInfo(id, code, name)`. Igual que PC-1, no filtra por estado;
3. cualquier error de base → `DependencyUnavailableError("product-catalog")`, el mismo `503` de hoy, con causa
   `contract:<causa>`; un código o nombre vacío → la misma indisponibilidad que hoy un cuerpo inesperado.

La consulta es síncrona y se ejecuta en un hilo (`run_in_threadpool`).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sio_auth import SioPermission
from sio_auth.permissions import has_permission
from sio_auth.tokens import TokenClaims
from sio_contract_read import chunked, contract_errors, read
from sqlalchemy import Engine
from starlette.concurrency import run_in_threadpool

from business_reporting_service.application.exceptions import (
    PRODUCT_CATALOG,
    DependencyUnavailableError,
    OwnerForbiddenError,
)
from business_reporting_service.application.ports import UnitInfo
from business_reporting_service.infrastructure.catalog import MAX_BATCH
from business_reporting_service.observability import SERVICE_LOGGER

logger = logging.getLogger(SERVICE_LOGGER)
_PRODUCTS_READ = SioPermission(PRODUCT_CATALOG, "products", "read")
OPERATION = "product_summaries"
_BASE_UNITS = (
    "SELECT p.id, u.id AS unit_id, u.code, u.name FROM contract.v1_products p "
    "LEFT JOIN contract.v1_units_of_measure u ON u.id = p.base_unit_id WHERE p.id = ANY(:ids)"
)


def _unavailable(cause: str) -> DependencyUnavailableError:
    return DependencyUnavailableError(PRODUCT_CATALOG, OPERATION, f"contract:{cause}")


class ContractProductCatalog:
    def __init__(self, *, engine: Engine, claims: TokenClaims | None) -> None:
        self._engine = engine
        self._claims = claims

    def _read(self, unique: list[UUID]) -> dict[UUID, UnitInfo | None]:
        found: dict[UUID, UnitInfo | None] = dict.fromkeys(unique)
        for batch in chunked(unique, MAX_BATCH):
            with contract_errors(_unavailable, dependency=PRODUCT_CATALOG):
                rows = read(self._engine, _BASE_UNITS, {"ids": batch})
            for row in rows:
                if row["unit_id"] is None:
                    continue
                code, name = row.get("code"), row.get("name")
                if not isinstance(code, str) or not isinstance(name, str):
                    raise _unavailable("cuerpo_inesperado")
                found[row["id"]] = UnitInfo(row["unit_id"], code, name)
        return found

    async def base_units(self, global_ids: list[UUID]) -> dict[UUID, UnitInfo | None]:
        unique = list(dict.fromkeys(global_ids))
        if not unique:
            return {}
        if self._claims is None or not has_permission(self._claims.permissions, _PRODUCTS_READ):
            logger.info("Product Catalog negó la lectura de productos estado=%s", 403)
            raise OwnerForbiddenError(PRODUCT_CATALOG, OPERATION)
        return await run_in_threadpool(self._read, unique)
