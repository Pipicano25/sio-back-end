from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from geography_service.domain.global_administrative_division import (
    AdministrativeDivisionStatus,
    AdministrativeDivisionType,
)


class GlobalAdministrativeDivisionCreate(BaseModel):
    country_id: UUID
    parent_division_id: UUID | None = None

    code: str = Field(
        min_length=1,
        max_length=40,
    )

    name: str = Field(
        min_length=1,
        max_length=160,
    )

    division_type: AdministrativeDivisionType
    status: AdministrativeDivisionStatus


class GlobalAdministrativeDivisionUpdate(BaseModel):
    country_id: UUID
    parent_division_id: UUID | None = None

    code: str = Field(
        min_length=1,
        max_length=40,
    )

    name: str = Field(
        min_length=1,
        max_length=160,
    )

    division_type: AdministrativeDivisionType
    status: AdministrativeDivisionStatus

    version: int = Field(
        ge=1,
        description="Versión conocida para control de concurrencia.",
    )


class GlobalAdministrativeDivisionResponse(BaseModel):
    """Representa una división administrativa expuesta por la API.

    Attributes:
        id: Identificador de la división administrativa.
        country_id: Identificador del país asociado.
        parent_division_id: Identificador de la división superior, si existe.
        code: Código de la división administrativa.
        name: Nombre de la división administrativa.
        division_type: Tipo de división administrativa.
        status: Estado funcional del registro.
        version: Versión utilizada para control de concurrencia.
        created_by: Usuario que creó el registro.
        updated_by: Usuario que realizó la última modificación.
        created_at: Fecha y hora de creación.
        updated_at: Fecha y hora de última modificación.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    country_id: UUID
    parent_division_id: UUID | None

    code: str
    name: str
    division_type: AdministrativeDivisionType

    status: AdministrativeDivisionStatus
    version: int

    created_by: str
    updated_by: str

    created_at: datetime
    updated_at: datetime
