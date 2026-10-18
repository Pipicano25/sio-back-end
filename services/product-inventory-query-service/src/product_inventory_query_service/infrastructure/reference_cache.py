"""Caché en memoria, de vida corta, de las unidades de medida (FR-022-02).

Es la **única** caché entre solicitudes del servicio: precios, existencias y políticas nunca se guardan. Las
unidades se usan solo para nombrar presentaciones (PC-3).
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from uuid import UUID

from product_inventory_query_service.application.ports import Reference

Loader = Callable[[list[UUID]], Awaitable[dict[UUID, Reference]]]


class UnitCache:
    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._entries: dict[UUID, tuple[float, Reference]] = {}

    async def get_many(self, ids: list[UUID], loader: Loader) -> dict[UUID, Reference]:
        now = self._clock()
        found: dict[UUID, Reference] = {}
        missing: list[UUID] = []
        for unit_id in dict.fromkeys(ids):
            entry = self._entries.get(unit_id)
            if entry is not None and entry[0] > now:
                found[unit_id] = entry[1]
            else:
                missing.append(unit_id)
        if missing:
            loaded = await loader(missing)
            expires = self._clock() + self._ttl
            for unit_id, unit in loaded.items():
                self._entries[unit_id] = (expires, unit)
                found[unit_id] = unit
        return found
