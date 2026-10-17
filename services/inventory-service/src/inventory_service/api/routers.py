"""Registro de los routers funcionales bajo `/api/v1`."""

from __future__ import annotations

from fastapi import FastAPI
from sio_auth import SIOAuth

from inventory_service.api import adjustments, counts, entries, inventory_reads, outputs, policies, queries, valuation


def include_api_routers(app: FastAPI, auth: SIOAuth, *, prefix: str) -> None:
    """Incluye los routers de entradas, salidas, saldos, kardex y operaciones."""
    app.include_router(entries.build_router(auth), prefix=prefix)
    app.include_router(outputs.build_router(auth), prefix=prefix)
    app.include_router(queries.build_router(auth), prefix=prefix)
    app.include_router(valuation.build_router(auth), prefix=prefix)
    app.include_router(adjustments.build_router(auth), prefix=prefix)
    app.include_router(counts.build_router(auth), prefix=prefix)
    app.include_router(policies.build_router(auth), prefix=prefix)
    app.include_router(inventory_reads.build_router(auth), prefix=prefix)  # spec 022: INV-1, INV-2, INV-3
