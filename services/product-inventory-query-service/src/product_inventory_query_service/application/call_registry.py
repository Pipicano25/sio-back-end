"""Registro de llamadas de una solicitud: cada operación con los mismos argumentos se ejecuta una sola vez
(FR-022-138, CP-101).

Vive solo durante la solicitud y se descarta al terminar; **no** es una caché entre solicitudes (FR-022-02). Si dos
partes de la solicitud piden lo mismo a la vez, comparten la misma tarea en curso.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Awaitable, Callable, Hashable
from typing import Any, TypeVar
from uuid import UUID

T = TypeVar("T")


def normalize(value: Any) -> Hashable:
    """Forma canónica y comparable de los argumentos (listas de ids sin orden ni duplicados)."""
    if isinstance(value, dict):
        return tuple(sorted((key, normalize(item)) for key, item in value.items()))
    if isinstance(value, (list, tuple, set, frozenset)):
        normalized = [normalize(item) for item in value]
        if all(isinstance(item, (UUID, str, int)) for item in value):
            return tuple(sorted(set(normalized), key=str))
        return tuple(normalized)
    return value


class CallRegistry:
    def __init__(self) -> None:
        self._tasks: dict[tuple[str, Hashable], asyncio.Task] = {}
        self.executed: Counter = Counter()

    async def once(self, operation: str, arguments: Any, factory: Callable[[], Awaitable[T]]) -> T:
        key = (operation, normalize(arguments))
        task = self._tasks.get(key)
        if task is None:
            self.executed[operation] += 1
            task = asyncio.ensure_future(factory())
            self._tasks[key] = task
        return await task

    def close(self) -> None:
        for task in self._tasks.values():
            if not task.done():
                task.cancel()
        self._tasks.clear()
