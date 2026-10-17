"""Registro de los routers funcionales bajo `/api/v1`.

Las cuatro consultas (`product-overviews`, `inventory-overviews`, `low-stock-products` e
`inventory-summary`) se agregan en las fases 10 a 13 de `tasks.md`.
"""

from __future__ import annotations

from fastapi import FastAPI
from sio_auth import SIOAuth


def include_api_routers(app: FastAPI, auth: SIOAuth, *, prefix: str) -> None:
    """Incluye los routers funcionales del servicio."""
    del app, auth, prefix
