"""Tipos y modelo base compartidos por los esquemas de la API."""

from decimal import Decimal
from typing import Annotated, Any, ClassVar, Generic, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, model_validator

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


OptionalVersion = Annotated[
    int | None,
    Field(default=None, ge=1, description="Versión conocida por el cliente. Opcional: si se envía y no coincide, responde 409."),
]


class StatusActionRequest(StrictModel):
    """Cuerpo de `deactivate` y `reactivate`: la versión es opcional y el cuerpo puede omitirse (D10)."""

    version: OptionalVersion = None


class PartialUpdate(StrictModel):
    """Base de un `PUT` parcial (constitución 4.0.0, D28).

    Un campo ausente no cambia; `null` borra un campo opcional y en uno de
    `not_nullable` responde `422`. Un cuerpo vacío o solo con `version` → `422`.
    """

    not_nullable: ClassVar[frozenset[str]] = frozenset()

    version: OptionalVersion = None

    @model_validator(mode="after")
    def _check_partial(self):
        sent = self.model_fields_set - {"version"}
        if not sent:
            raise ValueError("Envíe al menos un campo a modificar.")
        nulls = sorted(name for name in sent & self.not_nullable if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"Estos campos no admiten null: {', '.join(nulls)}.")
        return self

    def changes(self) -> dict[str, Any]:
        """Solo los campos enviados, sin `version`."""
        return self.model_dump(exclude_unset=True, exclude={"version"})


ItemT = TypeVar("ItemT")


class PaginatedResponse(BaseModel, Generic[ItemT]):
    """Formato de colección de SIO."""

    items: list[ItemT]
    page: int
    page_size: int
    total_records: int
    total_pages: int
