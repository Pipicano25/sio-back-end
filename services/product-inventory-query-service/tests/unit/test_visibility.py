"""Bloques visibles según los permisos del token (T076; FR-022-14, CP-58, CP-63)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sio_auth.permissions import extract_permission_grants
from sio_auth.tokens import TokenClaims

from product_inventory_query_service.api.visibility import Block, require_filter_blocks, visible_blocks
from product_inventory_query_service.application.exceptions import ForbiddenFilterError
from tests.conftest import USER_ROLES


def claims(*roles: str) -> TokenClaims:
    return TokenClaims(
        subject="sub", issuer="iss", audiences=("sio-api",), expires_at=datetime.now(UTC), roles=frozenset(roles),
        permissions=frozenset(extract_permission_grants(roles)), preferred_username=None, email=None, raw={},
    )


@pytest.mark.parametrize(
    ("user", "expected"),
    [
        ("admin.test", {Block.PRICES, Block.STOCK, Block.MINIMUMS}),
        ("supervisor.test", {Block.PRICES, Block.STOCK, Block.MINIMUMS}),
        ("ventas.test", {Block.PRICES, Block.STOCK}),
        ("inventario.test", {Block.STOCK, Block.MINIMUMS}),
        ("compras.test", set()),
    ],
)
def test_blocks_per_test_user(user, expected) -> None:
    assert visible_blocks(claims(*USER_ROLES[user])) == expected


def test_all_wildcards_in_any_segment() -> None:
    assert Block.STOCK in visible_blocks(claims("perm:product-inventory-query:all:read"))
    assert Block.MINIMUMS in visible_blocks(claims("perm:inventory:all:all"))
    assert Block.PRICES not in visible_blocks(claims("perm:commercial-relationship:price_list_items:update"))
    assert visible_blocks(claims("rol-sin-formato", "perm:mal")) == frozenset()


def test_there_is_no_valuation_block() -> None:
    """La valoración económica está fuera de la spec 022: ningún permiso, ni el comodín, la hace visible."""
    assert {block.value for block in Block} == {"PRICES", "STOCK", "MINIMUMS"}


def test_filters_of_invisible_blocks_are_403() -> None:
    sales = visible_blocks(claims(*USER_ROLES["ventas.test"]))
    require_filter_blocks({"stock_state", "search"}, sales)
    with pytest.raises(ForbiddenFilterError):
        require_filter_blocks({"minimum_state"}, sales)
    with pytest.raises(ForbiddenFilterError):
        require_filter_blocks({"stock_state"}, visible_blocks(claims()))
