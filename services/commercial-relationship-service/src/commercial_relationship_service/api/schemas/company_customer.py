"""Esquemas de clientes (`contracts/rest-api.md` §2)."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from commercial_relationship_service.api.schemas.common import (
    AuditedResponse,
    DisplayName,
    InternalCode,
    StrictModel,
    UpdateModel,
)


class CompanyCustomerCreate(StrictModel):
    """Alta (FR-020): la combinación tipo–identidad la valida el dominio."""

    customer_kind: Literal["PERSON", "ORGANIZATION"]
    person_identity_id: UUID | None = None
    organization_identity_id: UUID | None = None
    internal_code: InternalCode
    display_name: DisplayName
    preferred_contact_person_id: UUID | None = None


class CompanyCustomerUpdate(UpdateModel):
    """`PUT` (FR-024, DS-17)."""

    immutable_fields = frozenset(
        {"customer_kind", "person_identity_id", "organization_identity_id", "company_id", "status"}
    )

    internal_code: InternalCode
    display_name: DisplayName
    preferred_contact_person_id: UUID | None = None


class CompanyCustomerResponse(AuditedResponse):
    """Representación de un cliente; sin datos de Party Identity."""

    customer_kind: str
    person_identity_id: UUID | None
    organization_identity_id: UUID | None
    internal_code: str
    display_name: str
    preferred_contact_person_id: UUID | None
