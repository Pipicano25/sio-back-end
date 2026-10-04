"""Tipos y modelos base compartidos por los esquemas de la API (`contracts/rest-api.md`).

- `StrictModel` rechaza campos desconocidos (`422 VALIDATION_ERROR`): el cuerpo
  nunca fija `created_by`, `updated_by`, `status` ni `company_id` en altas.
- `UpdateModel` rechaza con el tipo `immutable_field` los campos que el `PUT` no
  permite cambiar (`422 IMMUTABLE_FIELD`, DS-05).
- Los importes se reciben como número o cadena y se devuelven **siempre** como
  cadena decimal con la escala de su columna, nunca como número JSON (R-10).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, ClassVar, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, PlainSerializer, model_validator
from pydantic_core import PydanticCustomError


def _strip(value: Any) -> Any:
    return value.strip() if isinstance(value, str) else value


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _reject_bool(value: Any) -> Any:
    if isinstance(value, bool):
        raise ValueError("El importe debe ser un número decimal.")
    return value


InternalCode = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=60)]
DisplayName = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=200)]
ReferenceCode = Annotated[
    Annotated[str, Field(max_length=100)] | None, BeforeValidator(_blank_to_none)
]
ShortName = Annotated[Annotated[str, Field(max_length=160)] | None, BeforeValidator(_blank_to_none)]
CurrencyCode = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=10)]
BlockReason = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=500)]
SalePriceIn = Annotated[
    Decimal, BeforeValidator(_reject_bool), Field(ge=0, max_digits=18, decimal_places=2)
]
ReferenceCostIn = Annotated[
    Decimal, BeforeValidator(_reject_bool), Field(ge=0, max_digits=18, decimal_places=4)
]
Version = Annotated[int, Field(ge=1)]


def _money(places: int):
    quantum = Decimal(1).scaleb(-places)
    return PlainSerializer(lambda value: format(Decimal(value).quantize(quantum), "f"), return_type=str)


SalePriceOut = Annotated[Decimal, _money(2)]
ReferenceCostOut = Annotated[Decimal, _money(4)]


class StrictModel(BaseModel):
    """Modelo de entrada que rechaza campos desconocidos."""

    model_config = ConfigDict(extra="forbid")


class UpdateModel(StrictModel):
    """Cuerpo de `PUT` con versión esperada y campos inmutables declarados."""

    immutable_fields: ClassVar[frozenset[str]] = frozenset()

    version: Version

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


class VersionRequest(StrictModel):
    """Cuerpo de `deactivate`, `reactivate` y `unblock`: solo la versión esperada (D10)."""

    version: Version


class AuditedResponse(BaseModel):
    """Campos comunes de lectura."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    status: str
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime


ItemT = TypeVar("ItemT")


class PaginatedResponse(BaseModel, Generic[ItemT]):
    """Formato de colección de SIO."""

    items: list[ItemT]
    page: int
    page_size: int
    total_records: int
    total_pages: int
