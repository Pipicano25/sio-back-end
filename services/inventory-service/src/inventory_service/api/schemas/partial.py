"""Base de un `PUT` parcial (constitución 4.0.0, D28)."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError


class PartialUpdate(BaseModel):
    """Un campo ausente no cambia; `null` en uno de `not_nullable` → `422`.

    Un cuerpo vacío o solo con `version` → `422`. `version` es opcional (D9).
    """

    model_config = ConfigDict(extra="forbid")

    not_nullable: ClassVar[frozenset[str]] = frozenset()

    version: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _check_partial(self):
        sent = self.model_fields_set - {"version"}
        if not sent:
            raise PydanticCustomError("INVALID_FORMAT", "Envíe al menos un campo a modificar.")
        nulls = sorted(name for name in sent & self.not_nullable if getattr(self, name) is None)
        if nulls:
            raise PydanticCustomError("INVALID_FORMAT", f"Estos campos no admiten null: {', '.join(nulls)}.")
        return self

    def changes(self) -> dict[str, Any]:
        """Solo los campos enviados, sin `version`."""
        return self.model_dump(exclude_unset=True, exclude={"version"})
