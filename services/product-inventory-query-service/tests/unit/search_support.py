"""Conductor y evaluadores simulados para las pruebas de búsqueda progresiva y paginación."""

from __future__ import annotations

from product_inventory_query_service.domain.pagination import Candidate


class ListConductor:
    """Conductor sobre una lista ordenada `(clave_de_orden, id)`, con continuación *keyset* y empates."""

    def __init__(self, rows: list[tuple[str, str]]) -> None:
        self.rows = sorted(rows)
        self.calls: list[tuple[dict | None, int]] = []

    async def __call__(self, after: dict | None, limit: int):
        self.calls.append((after, limit))
        rows = self.rows
        if after is not None:
            bound = (after["k"][0], after["id"])
            rows = [row for row in rows if row > bound]
        page = rows[: limit + 1]
        return [Candidate(row[1], {"k": [row[0]], "id": row[1]}, row) for row in page[:limit]], len(page) > limit


class SetEvaluator:
    """Acepta las claves de un conjunto; registra los lotes que recibe."""

    def __init__(self, accepted: set[str]) -> None:
        self.accepted = accepted
        self.batches: list[list[str]] = []

    async def __call__(self, candidates):
        self.batches.append([c.key for c in candidates])
        return {c.key for c in candidates if c.key in self.accepted}


def rows(n: int, *, ties: int = 1) -> list[tuple[str, str]]:
    """`n` filas con nombres que se repiten de a `ties` (empates en la clave de orden)."""
    return [(f"Producto {index // ties:04d}", f"id-{index:05d}") for index in range(n)]
