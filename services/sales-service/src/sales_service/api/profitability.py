"""Visibilidad de la rentabilidad (FR-027a, DS-12, C-08; research.md R-02).

Costo y margen solo se devuelven si el token tiene `perm:sales:sales:read-profitability`
(evaluado con `sio-auth`, incluidos sus comodines). Sin él, los campos se **omiten** del JSON
(no se envían como `null`, que en las líneas significa costo desconocido) en toda respuesta
que contenga una venta o líneas. El permiso no autoriza ninguna ruta por sí solo.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sio_auth.dependencies import get_current_claims
from sio_auth.models import SioPermission
from sio_auth.permissions import evaluate_permission

PROFITABILITY_PERMISSION = SioPermission(service="sales", resource="sales", action="read-profitability")

LINE_FIELDS = (
    "unit_cost_snapshot",
    "cost_total",
    "cost_known",
    "gross_margin_amount",
    "gross_margin_percentage",
)
HEADER_FIELDS = ("has_unknown_cost",)
_ALL = frozenset(LINE_FIELDS + HEADER_FIELDS)


def can_read_profitability(roles: Iterable[str]) -> bool:
    return evaluate_permission(roles, PROFITABILITY_PERMISSION)


def request_can_read_profitability(request: Request) -> bool:
    return can_read_profitability(get_current_claims(request).roles)


def strip_profitability(payload: Any) -> Any:
    """Copia de la respuesta sin los campos de rentabilidad, a cualquier profundidad."""
    if isinstance(payload, dict):
        return {key: strip_profitability(value) for key, value in payload.items() if key not in _ALL}
    if isinstance(payload, list):
        return [strip_profitability(item) for item in payload]
    return payload


def present(request: Request, model: BaseModel, *, status_code: int = 200) -> Response:
    """Respuesta JSON de una venta o líneas, sin rentabilidad si el token no tiene el permiso."""
    payload = jsonable_encoder(model)
    if not request_can_read_profitability(request):
        payload = strip_profitability(payload)
    return JSONResponse(status_code=status_code, content=payload)


def present_list(request: Request, models: list[BaseModel]) -> Response:
    payload = jsonable_encoder(models)
    if not request_can_read_profitability(request):
        payload = strip_profitability(payload)
    return JSONResponse(status_code=200, content=payload)
