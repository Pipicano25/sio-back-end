"""Bloques visibles de la respuesta según los permisos del token (FR-022-14; research R-04).

Usa los *grants* que ya interpreta `sio-auth` (`TokenClaims.permissions` y `SioGrant.allows`), incluidos los
comodines `all`; este servicio no reimplementa la interpretación de permisos (Principio V).

La valoración económica del inventario está fuera del alcance de la spec 022 (decisión del 2026-10-17): no hay un
bloque de valoración y este servicio nunca la devuelve.

| Bloque | Permiso |
|---|---|
| `PRICES` | `perm:commercial-relationship:price_list_items:read` |
| `STOCK` | `perm:product-inventory-query:stock:read` |
| `MINIMUMS` | `perm:inventory:product-policies:read` |
"""

from __future__ import annotations

from enum import Enum

from sio_auth import SioPermission
from sio_auth.tokens import TokenClaims

from product_inventory_query_service.application.exceptions import ForbiddenFilterError


class Block(str, Enum):
    PRICES = "PRICES"
    STOCK = "STOCK"
    MINIMUMS = "MINIMUMS"


BLOCK_PERMISSIONS: dict[Block, SioPermission] = {
    Block.PRICES: SioPermission(service="commercial-relationship", resource="price_list_items", action="read"),
    Block.STOCK: SioPermission(service="product-inventory-query", resource="stock", action="read"),
    Block.MINIMUMS: SioPermission(service="inventory", resource="product-policies", action="read"),
}

FILTER_BLOCKS: dict[str, Block] = {"stock_state": Block.STOCK, "minimum_state": Block.MINIMUMS}
"""Filtros que dependen de un bloque: sin él, `403` (FR-022-14)."""


def visible_blocks(claims: TokenClaims) -> frozenset[Block]:
    return frozenset(
        block for block, required in BLOCK_PERMISSIONS.items() if any(grant.allows(required) for grant in claims.permissions)
    )


def require_filter_blocks(used_filters: set[str], blocks: frozenset[Block]) -> None:
    """`403` si se usa un filtro de un bloque que el usuario no puede ver."""
    for name in sorted(used_filters):
        block = FILTER_BLOCKS.get(name)
        if block is not None and block not in blocks:
            raise ForbiddenFilterError("No tiene permiso para usar este filtro.")
