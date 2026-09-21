from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID


GlobalCityStatus = Literal[
    "ACTIVE",
    "INACTIVE",
]


@dataclass(frozen=True, slots=True)
class GlobalCity:
    """Representa una ciudad global dentro del dominio geográfico.

    Esta entidad no depende de FastAPI, SQLAlchemy, PostgreSQL ni sio-auth.
    Contiene únicamente la información de dominio necesaria para representar
    una ciudad dentro de SIO.

    Attributes:
        id: Identificador global de la ciudad.
        country_id: Identificador del país al que pertenece.
        administrative_division_id: División administrativa asociada, si existe.
        code: Código oficial de la ciudad cuando esté disponible.
        name: Nombre oficial de la ciudad.
        latitude: Latitud aproximada del centroide.
        longitude: Longitud aproximada del centroide.
        status: Estado funcional del registro.
        version: Versión utilizada para control de concurrencia optimista.
        created_by: Identificador del usuario que creó el registro.
        updated_by: Identificador del usuario que realizó la última modificación.
        created_at: Fecha y hora de creación.
        updated_at: Fecha y hora de última modificación.
    """

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
