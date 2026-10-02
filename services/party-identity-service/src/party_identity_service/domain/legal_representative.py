"""Entidad de dominio de representantes legales (Fase B)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from party_identity_service.domain.contact import normalize_optional_text

RepresentativeType = Literal["PRIMARY", "ALTERNATE", "OTHER"]

SOURCE_DOCUMENT_REFERENCE_MAX_LENGTH = 1000


def normalize_document_reference(value: str | None) -> str | None:
    """Recorta; vacío → `None` (DS-13). La longitud la valida la API."""
    return normalize_optional_text(value)


def is_primary_type(representative_type: RepresentativeType) -> bool:
    """`is_primary` se deriva del tipo: `PRIMARY` ⇔ principal (DS-06, C-04)."""
    return representative_type == "PRIMARY"


@dataclass(frozen=True, slots=True)
class LegalRepresentative:
    """Relación histórica organización–representante (estándar 4.16)."""

    id: UUID
    organization_identity_id: UUID
    person_identity_id: UUID
    representative_type: RepresentativeType
    position: str | None
    is_primary: bool
    is_active: bool
    valid_from: datetime
    valid_to: datetime | None
    source_document_reference: str | None
    version: int
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime
