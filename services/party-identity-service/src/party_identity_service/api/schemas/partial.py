"""Base de los cuerpos de `PUT` parcial (constitución 4.0.0, D28 y D9).

- Solo se envían los campos que cambian; un campo ausente no cambia.
- `null` borra un campo opcional; en un campo obligatorio (`not_nullable`) responde `422`.
- Un cuerpo sin campos para modificar (vacío o solo con `version`) responde `422`.
- `version` es opcional: si llega, se valida (`409` si no coincide).
"""

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PartialUpdate(BaseModel):
    """Cuerpo de un `PUT` parcial."""

    model_config = ConfigDict(extra="forbid")

    not_nullable: ClassVar[frozenset[str]] = frozenset()
    """Campos que no admiten `null` cuando se envían."""

    ignored_for_emptiness: ClassVar[frozenset[str]] = frozenset({"version"})
    """Campos que no cuentan como modificación (solo control)."""

    version: int | None = Field(
        default=None,
        ge=1,
        description="Versión conocida por el cliente. Opcional: si se envía y no coincide, responde 409.",
    )

    @model_validator(mode="after")
    def _check_partial(self) -> "PartialUpdate":
        sent = self.model_fields_set - self.ignored_for_emptiness
        if not sent:
            raise ValueError("Envíe al menos un campo a modificar.")
        nulls = sorted(name for name in sent & self.not_nullable if getattr(self, name) is None)
        if nulls:
            raise ValueError(f"Estos campos no admiten null: {', '.join(nulls)}.")
        return self

    def changes(self, *, exclude: set[str] | frozenset[str] = frozenset()) -> dict[str, Any]:
        """Campos enviados, sin `version` ni los excluidos."""
        return self.model_dump(exclude_unset=True, exclude={"version", *exclude})
