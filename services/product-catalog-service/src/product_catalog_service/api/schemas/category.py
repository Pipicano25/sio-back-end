"""Esquemas de categorías (`contracts/rest-api.md` §4)."""

from uuid import UUID

from pydantic import Field

from product_catalog_service.api.schemas.base import (
    RequestModel,
    StatusResourceResponse,
    UpdateModel,
)


class CategoryCreate(RequestModel):
    code: str = Field(max_length=100)
    name: str = Field(max_length=240)
    description: str | None = None
    parent_category_id: UUID | None = None


class CategoryUpdate(UpdateModel):
    immutable_fields = frozenset({"code", "status"})

    name: str = Field(max_length=240)
    description: str | None = None
    parent_category_id: UUID | None = None


class CategoryResponse(StatusResourceResponse):
    code: str
    name: str
    description: str | None
    parent_category_id: UUID | None
