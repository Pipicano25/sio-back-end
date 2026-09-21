from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


GlobalCountryStatus = Literal[
    "ACTIVE",
    "INACTIVE",
]


@dataclass(frozen=True, slots=True)
class GlobalCountry:
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