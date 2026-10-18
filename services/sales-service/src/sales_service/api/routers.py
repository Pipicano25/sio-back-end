"""Registro de los routers funcionales bajo `/api/v1`."""

from __future__ import annotations

from fastapi import FastAPI
from sio_auth import SIOAuth

from sales_service.api import availability, operations, sales, sales_aggregates, sequences


def include_api_routers(app: FastAPI, auth: SIOAuth, *, prefix: str) -> None:
    app.include_router(sales.build_router(auth), prefix=prefix)
    app.include_router(operations.build_router(auth), prefix=prefix)
    app.include_router(availability.build_router(auth), prefix=prefix)
    app.include_router(sequences.build_router(auth), prefix=prefix)
    app.include_router(sales_aggregates.build_router(auth), prefix=prefix)
