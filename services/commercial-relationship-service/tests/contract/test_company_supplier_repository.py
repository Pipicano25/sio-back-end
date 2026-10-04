"""Repositorio de proveedores (RC-04, R-08)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from commercial_relationship_service.application.exceptions import (
    DuplicateInternalCodeError,
    DuplicateSupplierError,
)
from commercial_relationship_service.infrastructure.repositories import CompanySupplierRepository


def test_duplicates(db_session):
    repository = CompanySupplierRepository(db_session)
    company, organization = uuid4(), uuid4()
    repository.create(company_id=company, organization_identity_id=organization, internal_code="S-1",
                      display_name="P", created_by="s", updated_by="s")

    assert repository.organization_exists(company, organization)
    assert not repository.organization_exists(uuid4(), organization)

    with pytest.raises(DuplicateSupplierError):
        repository.create(company_id=company, organization_identity_id=organization, internal_code="S-2",
                          display_name="P", created_by="s", updated_by="s")
    with pytest.raises(DuplicateInternalCodeError):
        repository.create(company_id=company, organization_identity_id=uuid4(), internal_code="s-1",
                          display_name="P", created_by="s", updated_by="s")
