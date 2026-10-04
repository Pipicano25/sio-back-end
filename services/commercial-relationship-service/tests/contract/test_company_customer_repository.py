"""Repositorio de clientes (RC-04, R-08)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from commercial_relationship_service.application.exceptions import (
    DuplicateCustomerError,
    DuplicateInternalCodeError,
)
from commercial_relationship_service.infrastructure.repositories import CompanyCustomerRepository


def _person(company, person=None, code="C-1"):
    return {
        "company_id": company,
        "customer_kind": "PERSON",
        "person_identity_id": person or uuid4(),
        "internal_code": code,
        "display_name": "Cliente",
        "created_by": "s",
        "updated_by": "s",
    }


def test_duplicates_in_any_state(db_session):
    repository = CompanyCustomerRepository(db_session)
    company, person = uuid4(), uuid4()
    created = repository.create(**_person(company, person, code="ABC"))
    model = repository.load_for_update(created.id, expected_version=1)
    model.status = "INACTIVE"
    repository.save(model, duplicates={})

    assert repository.identity_exists(company, person_identity_id=person, organization_identity_id=None)
    assert repository.code_taken(company, "abc")

    with pytest.raises(DuplicateCustomerError):
        repository.create(**_person(company, person, code="OTRO"))
    with pytest.raises(DuplicateInternalCodeError):
        repository.create(**_person(company, code="Abc"))
