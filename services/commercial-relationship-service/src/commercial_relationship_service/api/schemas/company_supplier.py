"""Esquemas de proveedores (`contracts/rest-api.md` §3)."""

from __future__ import annotations

from uuid import UUID

from commercial_relationship_service.api.schemas.common import (
    AuditedResponse,
    BlockReason,
    DisplayName,
    InternalCode,
    StrictModel,
    UpdateModel,
    Version,
)


class CompanySupplierCreate(StrictModel):
    """Selección (FR-030)."""

    organization_identity_id: UUID
    internal_code: InternalCode
    display_name: DisplayName
    preferred_contact_person_id: UUID | None = None


class CompanySupplierUpdate(UpdateModel):
    """`PUT` (FR-034, DS-17): nunca cambia `status` ni `block_reason`."""

    immutable_fields = frozenset(
        {"organization_identity_id", "company_id", "status", "block_reason"}
    )

    internal_code: InternalCode
    display_name: DisplayName
    preferred_contact_person_id: UUID | None = None


class SupplierBlockRequest(StrictModel):
    """Bloqueo con motivo obligatorio (FR-033a)."""

    block_reason: BlockReason
    version: Version


class CompanySupplierResponse(AuditedResponse):
    """Representación de un proveedor; `block_reason` solo con `BLOCKED`."""

    organization_identity_id: UUID
    internal_code: str
    display_name: str
    preferred_contact_person_id: UUID | None
    block_reason: str | None
