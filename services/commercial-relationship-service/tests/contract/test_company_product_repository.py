"""Repositorio de productos empresariales (RC-04, R-08)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from commercial_relationship_service.application.exceptions import (
    DuplicateAdoptionError,
    DuplicateInternalCodeError,
)
from commercial_relationship_service.infrastructure.repositories import CompanyProductRepository


def _fields(company_id, product_id=None, code="000045"):
    return {
        "company_id": company_id,
        "global_product_id": product_id or uuid4(),
        "internal_code": code,
        "display_name": "Producto",
        "currency_code": "COP",
        "created_by": "sub",
        "updated_by": "sub",
    }


def test_create_and_read(db_session):
    repository = CompanyProductRepository(db_session)
    created = repository.create(**_fields(uuid4()))
    loaded = repository.get(created.id)
    assert loaded.internal_code == "000045"
    assert loaded.version == 1 and loaded.status == "ACTIVE"
    assert not db_session.in_transaction()


def test_duplicate_detection_in_any_state(db_session):
    repository = CompanyProductRepository(db_session)
    company, product = uuid4(), uuid4()
    created = repository.create(**_fields(company, product, code="ABC-1"))

    model = repository.load_for_update(created.id, expected_version=1)
    model.status = "INACTIVE"
    repository.save(model, duplicates={})

    assert repository.adoption_exists(company, product)
    assert repository.code_taken(company, "abc-1")
    assert not repository.code_taken(company, "abc-1", exclude_id=created.id)
    assert not repository.code_taken(uuid4(), "abc-1")


def test_integrity_errors_are_translated_by_constraint_name(db_session):
    repository = CompanyProductRepository(db_session)
    company, product = uuid4(), uuid4()
    repository.create(**_fields(company, product, code="A"))

    with pytest.raises(DuplicateAdoptionError) as error:
        repository.create(**_fields(company, product, code="B"))
    assert error.value.field == "global_product_id"

    with pytest.raises(DuplicateInternalCodeError) as error:
        repository.create(**_fields(company, code="a"))
    assert error.value.field == "internal_code"
