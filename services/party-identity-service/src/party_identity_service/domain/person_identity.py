"""Entidad de dominio para identidades globales de personas."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID


PersonIdentificationType = str

PersonVerificationStatus = Literal[
    "UNVERIFIED",
    "VERIFIED",
    "SUSPENDED",
]

IdentityStatus = Literal[
    "ACTIVE",
    "INACTIVE",
]
"""Estado de uso (DS-02), independiente de `verification_status`."""


@dataclass(frozen=True, slots=True)
class PersonIdentity:
    """Representa la identidad global de una persona natural.

    Attributes:
        id: Identificador global de la persona.
        identification_country_id: País externo emisor o asociado con
            la identificación.
        identification_type: Tipo de identificación normalizado.
        identification_number: Número de identificación normalizado.
        first_name: Primer nombre.
        middle_name: Segundo nombre.
        last_name: Primer apellido.
        second_last_name: Segundo apellido.
        birth_date: Fecha de nacimiento, cuando se conozca.
        verification_status: Estado de verificación de la identidad.
        status: Estado de uso (`ACTIVE`/`INACTIVE`).
        version: Versión para concurrencia optimista.
        created_by: Usuario que creó el registro.
        updated_by: Usuario que realizó la última modificación.
        created_at: Fecha de creación.
        updated_at: Fecha de última modificación.
    """

    id: UUID
    identification_country_id: UUID
    identification_type: PersonIdentificationType
    identification_number: str
    first_name: str
    middle_name: str | None
    last_name: str
    second_last_name: str | None
    birth_date: date | None
    verification_status: PersonVerificationStatus
    status: IdentityStatus
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
