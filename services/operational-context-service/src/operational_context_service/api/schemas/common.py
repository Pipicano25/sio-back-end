"""Tipos y modelo base compartidos por los esquemas de la API."""

from decimal import Decimal
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field

from operational_context_service.domain.location import normalize_coordinate


class StrictModel(BaseModel):
    """Modelo de entrada que rechaza campos desconocidos (`422`).

    Así el cuerpo nunca puede fijar `created_by`, `updated_by`, `status` ni
    datos que el servicio no guarda (RC-10, DS-01, DS-13).
    """

    model_config = ConfigDict(extra="forbid")


def _blank_to_none(value: Any) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _coordinate(field: str):
    def convert(value: Any) -> Decimal | None:
        if isinstance(value, bool):
            raise ValueError("La coordenada debe ser un número decimal.")
        return normalize_coordinate(value, field=field)

    return convert


OptionalEmail = Annotated[EmailStr | None, BeforeValidator(_blank_to_none)]
Phone = Annotated[Annotated[str, Field(max_length=40)] | None, BeforeValidator(_blank_to_none)]
AddressLine = Annotated[str | None, BeforeValidator(_blank_to_none)]
PostalCode = Annotated[Annotated[str, Field(max_length=20)] | None, BeforeValidator(_blank_to_none)]
Latitude = Annotated[Decimal | None, BeforeValidator(_coordinate("latitude"))]
Longitude = Annotated[Decimal | None, BeforeValidator(_coordinate("longitude"))]
TimezoneText = Annotated[str, Field(min_length=1, max_length=60)]
OptionalTimezoneText = Annotated[
    Annotated[str, Field(max_length=60)] | None,
    BeforeValidator(_blank_to_none),
]
Version = Annotated[int, Field(ge=1)]


class StatusActionRequest(StrictModel):
    """Cuerpo de `deactivate` y `reactivate`: solo la versión esperada (D10)."""

    version: Version


ItemT = TypeVar("ItemT")


class PaginatedResponse(BaseModel, Generic[ItemT]):
    """Formato de colección de SIO."""

    items: list[ItemT]
    page: int
    page_size: int
    total_records: int
    total_pages: int
