"""Caché de unidades (T074; FR-022-02)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

from product_inventory_query_service.application.ports import Reference
from product_inventory_query_service.infrastructure.reference_cache import UnitCache


def test_units_are_cached_for_300_seconds_and_only_missing_are_loaded() -> None:
    a, b = uuid4(), uuid4()
    units = {a: Reference(a, "TAB", "Tableta"), b: Reference(b, "CAJ", "Caja")}
    loaded: list[list] = []
    clock = {"now": 0.0}

    async def loader(ids):
        loaded.append(list(ids))
        return {i: units[i] for i in ids}

    cache = UnitCache(300, clock=lambda: clock["now"])

    async def run():
        assert await cache.get_many([a], loader) == {a: units[a]}
        assert await cache.get_many([a, b], loader) == units
        clock["now"] = 299
        await cache.get_many([a, b], loader)
        clock["now"] = 301
        await cache.get_many([a], loader)

    asyncio.run(run())
    assert loaded == [[a], [b], [a]]


def test_only_units_are_cached_in_the_service() -> None:
    """Ningún otro módulo guarda precios, saldos ni políticas entre solicitudes."""
    from pathlib import Path

    package = Path(__file__).resolve().parents[2] / "src" / "product_inventory_query_service"
    caches = [path.name for path in package.rglob("*.py") if "Cache" in path.read_text(encoding="utf-8")]
    assert sorted(caches) == ["reference_cache.py"]
