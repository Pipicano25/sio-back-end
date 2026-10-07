"""Registro de los routers funcionales bajo `/api/v1`."""

from __future__ import annotations

from fastapi import FastAPI
from sio_auth import SIOAuth

from purchase_service.api import lifecycle_events, operations, purchases, sequences


def include_api_routers(app: FastAPI, auth: SIOAuth, *, prefix: str) -> None:
    app.include_router(purchases.build_router(auth), prefix=prefix)
    app.include_router(operations.build_router(auth), prefix=prefix)
    app.include_router(lifecycle_events.build_router(auth), prefix=prefix)
    app.include_router(sequences.build_router(auth), prefix=prefix)
