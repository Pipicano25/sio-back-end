"""Registro de los routers funcionales bajo `/api/v1` (contrato §1)."""

from __future__ import annotations

from fastapi import FastAPI
from sio_auth import SIOAuth

from product_inventory_query_service.api import inventory_overviews, inventory_summary, low_stock_products, product_overviews


def include_api_routers(app: FastAPI, auth: SIOAuth, *, prefix: str) -> None:
    """Incluye los routers de las cuatro consultas (cada uno con su variante `/branches/{branch_id}/…`)."""
    for module in (product_overviews, inventory_overviews, low_stock_products, inventory_summary):
        app.include_router(module.build_router(auth), prefix=prefix)
