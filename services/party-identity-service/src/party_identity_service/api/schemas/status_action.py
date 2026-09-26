"""Schema HTTP de las acciones de estado (`deactivate` / `reactivate`)."""

from pydantic import BaseModel, ConfigDict, Field


class StatusActionRequest(BaseModel):
    """Cuerpo de una acción de estado con la versión esperada (DS-11)."""

    model_config = ConfigDict(
        extra="forbid",
    )

    version: int = Field(
        ge=1,
        description="Versión conocida por el cliente.",
    )
