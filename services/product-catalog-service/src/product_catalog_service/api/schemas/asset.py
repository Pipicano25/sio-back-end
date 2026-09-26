"""Esquemas de activos digitales (`contracts/rest-api.md` §6.7)."""

from typing import Literal

from pydantic import Field

from product_catalog_service.api.schemas.base import RequestModel, UpdateModel

AssetType = Literal["IMAGE", "TECHNICAL_SHEET", "MANUAL", "CERTIFICATE", "OTHER"]


class AssetCreate(RequestModel):
    asset_type: AssetType
    file_name: str = Field(max_length=510)
    storage_uri: str = Field(max_length=4000)
    mime_type: str | None = Field(default=None, max_length=240)
    is_primary: bool = False


class AssetUpdate(UpdateModel):
    immutable_fields = frozenset({"asset_type", "global_product_id", "status", "is_primary"})

    file_name: str = Field(max_length=510)
    storage_uri: str = Field(max_length=4000)
    mime_type: str | None = Field(default=None, max_length=240)
