"""Base de un `PUT` parcial (constitución 4.0.0, D28)."""

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PartialUpdate(BaseModel):
    """Un campo ausente no cambia; `null` borra uno opcional y en uno de `not_nullable` → `422`.

    Un cuerpo vacío o solo con `version` → `422`. `version` es opcional: si se envía y no
    coincide → `409`; si no, gana la última escritura (D9).
    """

    model_config = ConfigDict(extra="forbid")

    not_nullable: ClassVar[frozenset[str]] = frozenset()

    version: int | None = Field(
        default=None, ge=1, description="Versión conocida por el cliente. Opcional: si se envía y no coincide, responde 409."
    )

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
