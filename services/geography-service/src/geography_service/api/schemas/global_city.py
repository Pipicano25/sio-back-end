from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from geography_service.domain.global_city import (
    GlobalCityStatus,
)


Latitude = Annotated[
    Decimal,
    Field(
        ge=Decimal("-90"),
        le=Decimal("90"),
        max_digits=9,
        decimal_places=6,
        description="Latitud aproximada del centroide.",
        examples=[Decimal("6.244203")],
    ),
]


Longitude = Annotated[
    Decimal,
    Field(
        ge=Decimal("-180"),
        le=Decimal("180"),
        max_digits=9,
        decimal_places=6,
        description="Longitud aproximada del centroide.",
        examples=[Decimal("-75.581212")],
    ),
]


class GlobalCityCreate(BaseModel):
    """Representa los datos requeridos para crear una ciudad global.

    Attributes:
        country_id: País al que pertenece la ciudad.
        administrative_division_id: División administrativa opcional.
        code: Código oficial de la ciudad cuando exista.
        name: Nombre oficial.
        latitude: Latitud aproximada.
        longitude: Longitud aproximada.
        status: Estado inicial.
    """

    country_id: UUID
    administrative_division_id: UUID | None = None

    code: str | None = Field(
        default=None,
        max_length=40,
        description="Código oficial cuando exista.",
    )

    name: str = Field(
        min_length=1,
        max_length=160,
        description="Nombre oficial de la ciudad.",
        examples=["Medellín"],
    )

    latitude: Latitude | None = None
    longitude: Longitude | None = None

    status: GlobalCityStatus


class GlobalCityUpdate(BaseModel):
    """Representa una actualización completa de una ciudad global.

    Attributes:
        country_id: País al que pertenece la ciudad.
        administrative_division_id: División administrativa opcional.
        code: Código oficial cuando exista.
        name: Nombre oficial.
        latitude: Latitud aproximada.
        longitude: Longitud aproximada.
        status: Estado funcional.
        version: Versión conocida por el cliente.
    """

    country_id: UUID
    administrative_division_id: UUID | None = None

    code: str | None = Field(
        default=None,
        max_length=40,
    )

    name: str = Field(
        min_length=1,
        max_length=160,
    )

    latitude: Latitude | None = None
    longitude: Longitude | None = None

    status: GlobalCityStatus

    version: int = Field(
        ge=1,
        description=(
            "Versión conocida por el cliente para "
            "control de concurrencia."
        ),
    )


class GlobalCityResponse(BaseModel):
    """Representa una ciudad global expuesta mediante la API.

    Attributes:
        id: Identificador global de la ciudad.
        country_id: País asociado.
        administrative_division_id: División administrativa asociada.
        code: Código oficial cuando exista.
        name: Nombre oficial.
        latitude: Latitud aproximada.
        longitude: Longitud aproximada.
        status: Estado funcional.
        version: Versión actual.
        created_by: Usuario creador.
        updated_by: Usuario que realizó la última modificación.
        created_at: Fecha de creación.
        updated_at: Fecha de última modificación.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    country_id: UUID
    administrative_division_id: UUID | None

    code: str | None
    name: str

    latitude: Decimal | None
    longitude: Decimal | None

    status: GlobalCityStatus
    version: int

    created_by: str
    updated_by: str

    created_at: datetime
    updated_at: datetime
