from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from geography_service.domain.global_country import (
    GlobalCountryStatus,
)


Iso2Code = Annotated[
    str,
    Field(
        min_length=2,
        max_length=2,
        description="Código ISO 3166-1 alpha-2.",
        examples=["CO"],
    ),
]


Iso3Code = Annotated[
    str,
    Field(
        min_length=3,
        max_length=3,
        description="Código ISO 3166-1 alpha-3.",
        examples=["COL"],
    ),
]


CountryName = Annotated[
    str,
    Field(
        min_length=1,
        max_length=120,
        description="Nombre del país.",
        examples=["Colombia"],
    ),
]


PhonePrefix = Annotated[
    str | None,
    Field(
        max_length=10,
        description="Prefijo telefónico internacional.",
        examples=["+57"],
    ),
]


class GlobalCountryCreate(BaseModel):
    iso2_code: Iso2Code
    iso3_code: Iso3Code
    name: CountryName
    phone_prefix: PhonePrefix = None
    status: GlobalCountryStatus


class GlobalCountryUpdate(BaseModel):
    iso2_code: Iso2Code
    iso3_code: Iso3Code
    name: CountryName
    phone_prefix: PhonePrefix = None
    status: GlobalCountryStatus

    version: int = Field(
        ge=1,
        description=(
            "Versión conocida por el cliente para "
            "control de concurrencia."
        ),
    )


class GlobalCountryResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID

    iso2_code: str
    iso3_code: str
    name: str
    phone_prefix: str | None

    status: GlobalCountryStatus
    version: int

    created_by: str
    updated_by: str

    created_at: datetime
    updated_at: datetime
