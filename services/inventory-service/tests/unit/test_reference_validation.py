"""Validación de referencias con los dobles (R-07; T027)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from inventory_service.application.exceptions import DependencyUnavailableError, ValidationFailedError
from inventory_service.application.reference_validation import ReferenceValidator
from tests.fakes import FakeCommercialRelationship, FakeOperationalContext


@pytest.fixture
def setup():
    oc, cr = FakeOperationalContext(), FakeCommercialRelationship()
    company = uuid4()
    branch = oc.add_branch(company)
    user = oc.add_user(company)
    products = [cr.add_product(company) for _ in range(2)]
    return oc, cr, company, branch, user, products


def codes(error: ValidationFailedError) -> dict[str, str]:
    return {item["field"]: item["code"] for item in error.errors}


def test_valid_references_return_keycloak_user(setup) -> None:
    oc, cr, company, branch, user, products = setup
    result = ReferenceValidator(oc, cr).validate_operation(company, branch, user, [products[0], products[1], products[0]])
    assert result.keycloak_user_id == oc.users[user].keycloak_user_id
    assert cr.calls == [(products[0], products[1])]


def test_collects_every_invalid_reference(setup) -> None:
    oc, cr, company, branch, user, products = setup
    other = uuid4()
    inactive = cr.add_product(company, status="INACTIVE")
    with pytest.raises(ValidationFailedError) as error:
        ReferenceValidator(oc, cr).validate_operation(company, uuid4(), oc.add_user(other), [products[0], inactive, uuid4()])
    assert codes(error.value) == {
        "branch_id": "BRANCH_NOT_FOUND",
        "application_user_id": "APPLICATION_USER_NOT_FOUND",
        "lines[1].company_product_id": "COMPANY_PRODUCT_INACTIVE",
        "lines[2].company_product_id": "COMPANY_PRODUCT_NOT_FOUND",
    }


def test_reversal_user_accepts_inactive_but_not_other_company(setup) -> None:
    oc, cr, company, branch, user, products = setup
    validator = ReferenceValidator(oc, cr)
    inactive = oc.add_user(company, status="INACTIVE")
    assert validator.validate_reversal_user(company, inactive) == oc.users[inactive].keycloak_user_id
    with pytest.raises(ValidationFailedError) as error:
        validator.validate_reversal_user(company, oc.add_user(uuid4()))
    assert codes(error.value) == {"application_user_id": "APPLICATION_USER_NOT_FOUND"}
    assert cr.calls == []
    assert [call[0] for call in oc.technical_calls] == ["application_user", "application_user"]


def test_dependency_unavailable_propagates(setup) -> None:
    oc, cr, company, branch, user, products = setup
    cr.unavailable = True
    with pytest.raises(DependencyUnavailableError):
        ReferenceValidator(oc, cr).validate_operation(company, branch, user, products)
