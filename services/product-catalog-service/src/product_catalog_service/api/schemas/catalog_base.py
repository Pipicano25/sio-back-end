"""Esquemas de unidades de medida y tipos de empaque (`contracts/rest-api.md` §1–§2)."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from product_catalog_service.api.schemas.base import (
    RequestModel,
    StatusResourceResponse,
    UpdateModel,
)

MeasurementType = Literal["UNIT", "MASS", "VOLUME", "LENGTH", "AREA"]


class UnitOfMeasureCreate(RequestModel):
    code: str = Field(max_length=40)
    name: str = Field(max_length=160)
    symbol: str = Field(max_length=32)
    measurement_type: MeasurementType
    allows_decimals: bool


class UnitOfMeasureUpdate(UpdateModel):
    immutable_fields = frozenset({"code", "measurement_type", "allows_decimals", "status"})

    name: str = Field(max_length=160)
    symbol: str = Field(max_length=32)


class UnitOfMeasureResponse(StatusResourceResponse):
    code: str
    name: str
    symbol: str
    measurement_type: str
    allows_decimals: bool


class PackagingTypeCreate(RequestModel):
    code: str = Field(max_length=100)
    name: str = Field(max_length=240)
    description: str | None = None


class PackagingTypeUpdate(UpdateModel):
    immutable_fields = frozenset({"code", "status"})

    name: str = Field(max_length=240)
    description: str | None = None


class PackagingTypeResponse(StatusResourceResponse):
    code: str
    name: str
    description: str | None
