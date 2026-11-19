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


OPTIONAL_VERSION_DESCRIPTION = "Versión conocida por el cliente. Opcional: si se envía y no coincide, responde 409."


class UpdateModel(RequestModel):
    """`PUT` parcial (constitución 4.0.0, D28) con campos inmutables declarados.

    Solo se envían los campos que cambian; un campo ausente conserva su valor.
    `null` borra un campo opcional y en uno de `not_nullable` responde `422`.
    Un cuerpo vacío o solo con `version` → `422`. `version` es opcional (D9).
    """

    immutable_fields: ClassVar[frozenset[str]] = frozenset()
    not_nullable: ClassVar[frozenset[str]] = frozenset()

    version: int | None = Field(default=None, ge=1, description=OPTIONAL_VERSION_DESCRIPTION)

    @model_validator(mode="after")
    def _check_partial(self):
        sent = self.model_fields_set - {"version"}
        if not sent:
            raise ValueError("Envíe al menos un campo a modificar.")
        nulls = sorted(name for name in sent & self.not_nullable if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"Estos campos no admiten null: {', '.join(nulls)}.")
        return self

    def as_update(self) -> dict[str, Any]:
        """Argumentos del servicio: solo los campos enviados más `version`."""
        return {**self.model_dump(exclude_unset=True, exclude={"version"}), "version": self.version}

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
    """Cuerpo de las acciones de estado y de principal: versión opcional; el cuerpo puede omitirse (D10)."""

    version: int | None = Field(default=None, ge=1, description=OPTIONAL_VERSION_DESCRIPTION)


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
