"""Esquemas de atributos, opciones y atributos por categoría (`contracts/rest-api.md` §4–§5)."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from product_catalog_service.api.schemas.base import (
    RequestModel,
    StatusResourceResponse,
    UpdateModel,
)

DataType = Literal["TEXT", "INTEGER", "DECIMAL", "BOOLEAN", "DATE", "OPTION"]


class AttributeDefinitionCreate(RequestModel):
    code: str = Field(max_length=160)
    name: str = Field(max_length=240)
    description: str
    data_type: DataType
    unit_of_measure_id: UUID | None = None


class AttributeDefinitionUpdate(UpdateModel):
    immutable_fields = frozenset({"code", "data_type", "unit_of_measure_id", "status"})

    name: str = Field(max_length=240)
    description: str


class AttributeDefinitionResponse(StatusResourceResponse):
    code: str
    name: str
    description: str
    data_type: str
    unit_of_measure_id: UUID | None


class OptionCreate(RequestModel):
    code: str = Field(max_length=160)
    name: str = Field(max_length=240)
    description: str | None = None
    display_order: int = Field(default=0, ge=0, le=32767)


class OptionUpdate(UpdateModel):
    immutable_fields = frozenset({"code", "status", "attribute_definition_id"})

    name: str = Field(max_length=240)
    description: str | None = None
    display_order: int = Field(ge=0, le=32767)


class OptionResponse(StatusResourceResponse):
    attribute_definition_id: UUID
    code: str
    name: str
    description: str | None
    display_order: int


class CategoryAttributeCreate(RequestModel):
    attribute_definition_id: UUID
    is_required: bool = False
    is_filterable: bool = False
    display_order: int = Field(default=0, ge=0, le=32767)


class CategoryAttributeUpdate(UpdateModel):
    immutable_fields = frozenset({"attribute_definition_id", "global_category_id", "status"})

    is_required: bool
    is_filterable: bool
    display_order: int = Field(ge=0, le=32767)


class CategoryAttributeResponse(StatusResourceResponse):
    global_category_id: UUID
    attribute_definition_id: UUID
    is_required: bool
    is_filterable: bool
    display_order: int


class ApplicableAttributeResponse(BaseModel):
    attribute_definition_id: UUID
    code: str
    name: str
    data_type: str
    unit_of_measure_id: UUID | None
    is_required: bool
    is_filterable: bool
    display_order: int
    category_ids: list[UUID]
