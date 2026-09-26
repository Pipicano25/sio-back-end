"""Esquemas de tipos de grupo, grupos y asignaciones (`contracts/rest-api.md` §6.6, §7)."""

from uuid import UUID

from pydantic import Field

from product_catalog_service.api.schemas.base import (
    RequestModel,
    StatusResourceResponse,
    UpdateModel,
)


class GroupTypeCreate(RequestModel):
    code: str = Field(max_length=100)
    name: str = Field(max_length=240)
    description: str | None = None
    allows_multiple: bool = False
    display_order: int = Field(default=0, ge=0, le=32767)


class GroupTypeUpdate(UpdateModel):
    immutable_fields = frozenset({"code", "status"})

    name: str = Field(max_length=240)
    description: str | None = None
    allows_multiple: bool
    display_order: int = Field(ge=0, le=32767)


class GroupTypeResponse(StatusResourceResponse):
    code: str
    name: str
    description: str | None
    allows_multiple: bool
    display_order: int


class GroupCreate(RequestModel):
    code: str = Field(max_length=100)
    name: str = Field(max_length=320)
    description: str | None = None
    parent_group_id: UUID | None = None


class GroupUpdate(UpdateModel):
    immutable_fields = frozenset({"code", "group_type_id", "status"})

    name: str = Field(max_length=320)
    description: str | None = None
    parent_group_id: UUID | None = None


class GroupResponse(StatusResourceResponse):
    group_type_id: UUID
    parent_group_id: UUID | None
    code: str
    name: str
    description: str | None


class GroupAssignmentCreate(RequestModel):
    global_product_group_id: UUID
