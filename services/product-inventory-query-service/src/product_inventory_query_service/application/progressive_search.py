"""Búsqueda progresiva por lotes (FR-022-134 a FR-022-136; research R-07).

1. El conductor entrega un lote de `batch_size` candidatos posteriores a `after`, en su orden, y dice si tiene
   más.
2. Los evaluadores comprueban en paralelo sus filtros **solo** sobre los candidatos del lote y devuelven las
   claves que cumplen. Un candidato es válido si lo aceptan todos. Si un evaluador falla, la excepción se
   propaga (`503`): nunca se descartan candidatos por un fallo.
3. Los válidos conservan el orden del conductor; nada se reordena en memoria.
4. Se pide otro lote **solo** si faltan válidos (`need = page_size + 1`), el conductor tiene más y no se alcanzó
   el límite de trabajo (`max_batches` o el tiempo de trabajo, que se comprueba **entre** lotes: un lote iniciado
   se termina).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from product_inventory_query_service.domain.pagination import Candidate, SearchOutcome

Fetch = Callable[[dict | None, int], Awaitable[tuple[list[Candidate], bool]]]
Evaluate = Callable[[list[Candidate]], Awaitable[set[Any]]]


async def progressive_search(
    fetch: Fetch,
    evaluators: Sequence[Evaluate],
    *,
    need: int,
    batch_size: int,
    max_batches: int,
    work_time_seconds: float,
    after: dict | None = None,
    started_at: float | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> SearchOutcome:
    start = clock() if started_at is None else started_at
    valid: list[Candidate] = []
    examined = 0
    batches = 0
    last_examined = after

    while True:
        candidates, has_more = await fetch(last_examined, batch_size)
        batches += 1
        examined += len(candidates)
        if candidates:
            last_examined = candidates[-1].position
            accepted = None
            if evaluators:
                results = await asyncio.gather(*(evaluate(candidates) for evaluate in evaluators))
                accepted = set.intersection(*(set(result) for result in results))
            valid.extend(c for c in candidates if accepted is None or c.key in accepted)

        if len(valid) >= need:
            return SearchOutcome(valid, exhausted=False, limited=False, last_examined=last_examined,
                                 examined=examined, batches=batches)
        if not has_more or not candidates:
            return SearchOutcome(valid, exhausted=True, limited=False, last_examined=last_examined,
                                 examined=examined, batches=batches)
        if batches >= max_batches or clock() - start >= work_time_seconds:
            return SearchOutcome(valid, exhausted=False, limited=True, last_examined=last_examined,
                                 examined=examined, batches=batches)
