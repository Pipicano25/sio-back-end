"""Casos de uso de clientes (FR-020 a FR-028; R-06, R-07; DS-05, DS-08, DS-15, DS-17).

Orden del alta: cuerpo → unicidad local (identidad y código) → autorreferencia
(solo `ORGANIZATION`) → identidad → contacto. Nada se guarda ante un rechazo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from commercial_relationship_service.application.exceptions import (
    ContactPersonNotAllowedError,
    DuplicateCustomerError,
    DuplicateInternalCodeError,
)
from commercial_relationship_service.application.reference_validation import (
    reject_self_relationship,
    require_active_organization,
    require_active_person,
    require_valid_contact,
)
from commercial_relationship_service.domain.rules import (
    ORGANIZATION,
    PERSON,
    code_key,
    validate_customer_identity,
)
from commercial_relationship_service.domain.status import DEACTIVATE, REACTIVATE, next_status

EDITABLE_FIELDS = ("internal_code", "display_name", "preferred_contact_person_id")


class CompanyCustomerService:
    """Alta, mantenimiento y estados de clientes."""

    def __init__(self, repository, party_factory, company_directory_factory) -> None:
        self._repository = repository
        self._party_factory = party_factory
        self._companies_factory = company_directory_factory

    def create(self, company_id: UUID, values: dict[str, Any], *, actor: str):
        validate_customer_identity(
            customer_kind=values["customer_kind"],
            person_identity_id=values.get("person_identity_id"),
            organization_identity_id=values.get("organization_identity_id"),
            preferred_contact_person_id=values.get("preferred_contact_person_id"),
        )

        if self._repository.identity_exists(
            company_id,
            person_identity_id=values.get("person_identity_id"),
            organization_identity_id=values.get("organization_identity_id"),
        ):
            field = "person_identity_id" if values["customer_kind"] == PERSON else "organization_identity_id"
            raise DuplicateCustomerError(field=field)

        if self._repository.code_taken(company_id, values["internal_code"]):
            raise DuplicateInternalCodeError(field="internal_code")

        party = self._party_factory()

        if values["customer_kind"] == ORGANIZATION:
            organization_id = values["organization_identity_id"]
            reject_self_relationship(self._companies_factory(), company_id, organization_id)
            require_active_organization(party, organization_id)

            if values.get("preferred_contact_person_id") is not None:
                require_valid_contact(party, values["preferred_contact_person_id"], organization_id)
        else:
            require_active_person(party, values["person_identity_id"])

        return self._repository.create(
            company_id=company_id,
            customer_kind=values["customer_kind"],
            person_identity_id=values.get("person_identity_id"),
            organization_identity_id=values.get("organization_identity_id"),
            internal_code=values["internal_code"],
            display_name=values["display_name"],
            preferred_contact_person_id=values.get("preferred_contact_person_id"),
            created_by=actor,
            updated_by=actor,
        )

    def update(self, current, values: dict[str, Any], *, version: int, actor: str):
        """`PUT` en cualquier estado (DS-17); valida el contacto solo si cambia a no nulo."""
        contact_id = values.get("preferred_contact_person_id")

        if contact_id is not None and current.customer_kind == PERSON:
            raise ContactPersonNotAllowedError(field="preferred_contact_person_id")

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
        model.status = next_status(model.status, DEACTIVATE)
        _touch(model, actor)
        return self._repository.save(model, duplicates={})

    def reactivate(self, current, *, version: int, actor: str):
        """Revalida la identidad (FR-025); no revalida el contacto preferido (DS-08)."""
        next_status(current.status, REACTIVATE)
        party = self._party_factory()

        if current.customer_kind == PERSON:
            require_active_person(party, current.person_identity_id)
        else:
            require_active_organization(party, current.organization_identity_id)

        model = self._repository.load_for_update(current.id, expected_version=version)
        model.status = next_status(model.status, REACTIVATE)
        _touch(model, actor)
        return self._repository.save(model, duplicates={})


def _touch(model, actor: str) -> None:
    model.updated_by = actor
    model.updated_at = datetime.now(UTC)
