"""Contexto de una solicitud: presupuesto de tiempo y límite de concurrencia (RNF-022-3, research R-01).

La capa API abre un `RequestBudget` por solicitud. Cada llamada saliente usa como tiempo de espera el menor
entre el de la dependencia y lo que queda del presupuesto; si ya no queda, la llamada no sale y la solicitud
responde `503` completo (FR-022-71). El semáforo limita las llamadas simultáneas de la solicitud.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

Clock = Callable[[], float]


@dataclass
class RequestBudget:
    total_seconds: float
    max_parallel_calls: int
    clock: Clock = time.monotonic
    started_at: float = field(default=0.0)
    semaphore: asyncio.Semaphore = field(init=False)

    def __post_init__(self) -> None:
        self.started_at = self.clock()
        self.semaphore = asyncio.Semaphore(self.max_parallel_calls)

    def elapsed(self) -> float:
        return self.clock() - self.started_at

    def remaining(self) -> float:
        return self.total_seconds - self.elapsed()


_current: ContextVar[RequestBudget | None] = ContextVar("request_budget", default=None)


def current_budget() -> RequestBudget | None:
    return _current.get()


@contextmanager
def request_budget(budget: RequestBudget) -> Iterator[RequestBudget]:
    token = _current.set(budget)
    try:
        yield budget
    finally:
        _current.reset(token)
