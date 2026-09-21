from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


AdministrativeDivisionType = Literal[
    "DEPARTMENT",
    "STATE",
    "PROVINCE",
    "REGION",
    "DISTRICT",
    "OTHER",
]

AdministrativeDivisionStatus = Literal[
    "ACTIVE",
    "INACTIVE",
]


@dataclass(frozen=True, slots=True)
class GlobalAdministrativeDivision:
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