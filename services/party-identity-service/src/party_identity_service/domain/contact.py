"""Entidades de dominio de contactos (Fase B) y normalización compartida.

- `ContactProfile`: versión de un perfil de contacto de persona u organización.
- `ContactPerson`: persona de contacto de una organización.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

PartyKindLower = Literal["person", "organization"]
RelationState = Literal["active", "closed", "all"]


def normalize_optional_text(value: str | None) -> str | None:
    """Recorta espacios exteriores; una cadena vacía equivale a `None`."""
    if value is None:
        return None

    trimmed = value.strip()

    return trimmed or None


def normalize_email(value: str | None) -> str | None:
    """Recorta y pasa a minúsculas; vacío → `None` (FR-015)."""
    trimmed = normalize_optional_text(value)

    return trimmed.lower() if trimmed is not None else None


@dataclass(frozen=True, slots=True)
class ContactData:
    """Conjunto completo de datos de una versión de perfil (comparación no-op, DS-04)."""

    email: str | None
    phone: str | None
    address_line: str | None
    country_id: UUID | None
    administrative_division_id: UUID | None
    city_id: UUID | None
    postal_code: str | None

    @classmethod
    def normalized(
        cls,
        *,
        email: str | None,
        phone: str | None,
        address_line: str | None,
        country_id: UUID | None,
        administrative_division_id: UUID | None,
        city_id: UUID | None,
        postal_code: str | None,
    ) -> "ContactData":
        return cls(
            email=normalize_email(email),
            phone=normalize_optional_text(phone),
            address_line=normalize_optional_text(address_line),
            country_id=country_id,
            administrative_division_id=administrative_division_id,
            city_id=city_id,
            postal_code=normalize_optional_text(postal_code),
        )

    @property
    def has_contact(self) -> bool:
        """Al menos uno de correo, teléfono o dirección (FR-014, RN-03)."""
        return any((self.email, self.phone, self.address_line))

    @property
    def geography(self) -> tuple[UUID | None, UUID | None, UUID | None]:
        return (self.country_id, self.administrative_division_id, self.city_id)


@dataclass(frozen=True, slots=True)
class ContactProfile:
    """Versión de un perfil de contacto (estándar 4.11 y 4.13)."""

    id: UUID
    owner_id: UUID
    email: str | None
    phone: str | None
    address_line: str | None
    country_id: UUID | None
    administrative_division_id: UUID | None
    city_id: UUID | None
    postal_code: str | None
    is_active: bool
    valid_from: datetime
    valid_to: datetime | None
    confirmed_by_user_id: UUID
    confirmed_by_company_id: UUID
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    @property
    def data(self) -> ContactData:
        return ContactData(
            email=self.email,
            phone=self.phone,
            address_line=self.address_line,
            country_id=self.country_id,
            administrative_division_id=self.administrative_division_id,
            city_id=self.city_id,
            postal_code=self.postal_code,
        )


@dataclass(frozen=True, slots=True)
class ContactPerson:
    """Persona de contacto de una organización (estándar 4.14)."""

    id: UUID
    organization_identity_id: UUID
    person_identity_id: UUID | None
    position: str | None
    email: str | None
    phone: str | None
    is_primary: bool
    is_active: bool
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
