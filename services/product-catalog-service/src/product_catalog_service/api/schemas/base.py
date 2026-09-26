"""Esquemas base de solicitud y respuesta.

- `RequestModel` rechaza campos desconocidos (`extra="forbid"`): así ningún
  cuerpo puede traer datos de empresa (FR-001) ni fijar auditoría (RC-11).
- `UpdateModel` además rechaza con el tipo `immutable_field` los campos que la
  operación no permite modificar (R-05); se traducen a
  `422 PRODUCT_CATALOG.IMMUTABLE_FIELD`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

STATUS_PATTERN = "^(ACTIVE|INACTIVE)$"


class RequestModel(BaseModel):
    """Cuerpo de solicitud estricto."""

    model_config = ConfigDict(extra="forbid")


class UpdateModel(RequestModel):
    """Cuerpo de modificación con versión esperada y campos inmutables declarados."""

    immutable_fields: ClassVar[frozenset[str]] = frozenset()

    version: int = Field(ge=1, description="Versión esperada del registro.")

    @model_validator(mode="before")
    @classmethod
    def _reject_immutable(cls, data: Any) -> Any:
        if isinstance(data, dict):
            present = sorted(set(data) & cls.immutable_fields)
            if present:
                raise PydanticCustomError(
                    "immutable_field",
                    "Los campos {fields} no pueden modificarse.",
                    {"fields": ", ".join(present)},
                )
        return data


class VersionRequest(RequestModel):
    """Cuerpo de las acciones de estado y de principal."""

    version: int = Field(ge=1, description="Versión esperada del registro.")


class ResourceResponse(BaseModel):
    """Campos comunes de lectura."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    version: int
    created_at: datetime
    updated_at: datetime
    created_by: str
    updated_by: str


class StatusResourceResponse(ResourceResponse):
    status: str
