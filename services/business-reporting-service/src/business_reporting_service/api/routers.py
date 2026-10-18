"""Registro de los routers funcionales bajo `/api/v1`."""

from __future__ import annotations

from fastapi import FastAPI
from sio_auth import SIOAuth

from business_reporting_service.api import reports


def include_api_routers(app: FastAPI, auth: SIOAuth, *, prefix: str) -> None:
    """Incluye los cuatro reportes de la fase 1 (el margen es de la fase 2 de la spec 023)."""
    app.include_router(reports.build_router(auth), prefix=prefix)
