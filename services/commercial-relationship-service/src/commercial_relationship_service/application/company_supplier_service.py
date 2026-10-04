"""Casos de uso de proveedores (FR-030 a FR-035, FR-033a; DS-08, DS-10, DS-15, DS-16, DS-17).

`BLOCKED` exige motivo; desbloquear y reactivar revalidan la organización y no el
contacto preferido. El `PUT` nunca cambia el estado ni el motivo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from commercial_relationship_service.application.exceptions import (
    DuplicateInternalCodeError,
    DuplicateSupplierError,
)
from commercial_relationship_service.application.reference_validation import (
    reject_self_relationship,
    require_active_organization,
    require_valid_contact,
)
from commercial_relationship_service.domain.rules import code_key
from commercial_relationship_service.domain.status import (
    BLOCK,
    DEACTIVATE,
    REACTIVATE,
    UNBLOCK,
    next_status,
)

EDITABLE_FIELDS = ("internal_code", "display_name", "preferred_contact_person_id")


class CompanySupplierService:
    """Selección, mantenimiento, estados y bloqueo de proveedores."""

    def __init__(self, repository, party_factory, company_directory_factory) -> None:
        self._repository = repository
        self._party_factory = party_factory
        self._companies_factory = company_directory_factory

    def create(self, company_id: UUID, values: dict[str, Any], *, actor: str):
        organization_id = values["organization_identity_id"]

        if self._repository.organization_exists(company_id, organization_id):
            raise DuplicateSupplierError(field="organization_identity_id")

        if self._repository.code_taken(company_id, values["internal_code"]):
            raise DuplicateInternalCodeError(field="internal_code")

        reject_self_relationship(self._companies_factory(), company_id, organization_id)
        party = self._party_factory()
        require_active_organization(party, organization_id)

        if values.get("preferred_contact_person_id") is not None:
            require_valid_contact(party, values["preferred_contact_person_id"], organization_id)

        return self._repository.create(
            company_id=company_id,
            organization_identity_id=organization_id,
            internal_code=values["internal_code"],
            display_name=values["display_name"],
            preferred_contact_person_id=values.get("preferred_contact_person_id"),
            created_by=actor,
            updated_by=actor,
        )

    def update(self, current, values: dict[str, Any], *, version: int, actor: str):
        """`PUT` en `ACTIVE`, `INACTIVE` o `BLOCKED` (DS-17): no toca `status` ni `block_reason`."""
        contact_id = values.get("preferred_contact_person_id")

        if code_key(values["internal_code"]) != code_key(current.internal_code) and (
            self._repository.code_taken(current.company_id, values["internal_code"], exclude_id=current.id)
        ):
            raise DuplicateInternalCodeError(field="internal_code")

        if contact_id is not None and contact_id != current.preferred_contact_person_id:
            require_valid_contact(self._party_factory(), contact_id, current.organization_identity_id)

        model = self._repository.load_for_update(current.id, expected_version=version)

        if all(getattr(model, name) == values.get(name) for name in EDITABLE_FIELDS):
            self._repository.release()
            return model

        for name in EDITABLE_FIELDS:
            setattr(model, name, values.get(name))

        _touch(model, actor)
        return self._repository.save(model, duplicates=self._repository.duplicates)

    def deactivate(self, current, *, version: int, actor: str):
        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, DEACTIVATE, supplier=True)
        _touch(model, actor)
        return self._repository.save(model, duplicates={})

    def reactivate(self, current, *, version: int, actor: str):
        return self._to_active(current, REACTIVATE, version=version, actor=actor)

    def unblock(self, current, *, version: int, actor: str):
        return self._to_active(current, UNBLOCK, version=version, actor=actor)

    def block(self, current, *, block_reason: str, version: int, actor: str):
        """Bloquear no consulta Party Identity; exige motivo (FR-033a)."""
        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, BLOCK, supplier=True)
        model.block_reason = block_reason
        _touch(model, actor)
        return self._repository.save(model, duplicates={})

    def _to_active(self, current, action: str, *, version: int, actor: str):
        next_status(current.status, action, supplier=True)
        require_active_organization(self._party_factory(), current.organization_identity_id)

        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, action, supplier=True)
        model.block_reason = None
        _touch(model, actor)
        return self._repository.save(model, duplicates={})


def _touch(model, actor: str) -> None:
    model.updated_by = actor
    model.updated_at = datetime.now(UTC)
