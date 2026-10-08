"""Semántica `422`/`409` de las referencias (FR-002 a FR-005, FR-009, FR-030, C-01; T033).

`422`: no existe, es de otra empresa, no puede resolverse o es incoherente.
`409`: existe, pero su estado o configuración impide usarla.
`503`: la dependencia no está disponible.
"""

from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest

from tests.conftest import base, count_rows, line, sale_body


def create(seller, world, *lines, **header):
    return seller.post(f"{base(world)}/sales", json=sale_body(world, *lines, **header))


def assert_error(response, status: int, code: str, field: str | None = None) -> None:
    assert response.status_code == status, response.text
    body = response.json()
    expected = "SALES.VALIDATION_ERROR" if status == 422 else "SALES.REFERENCES_NOT_ELIGIBLE"
    assert body["code"] == expected
    codes = [error["code"] for error in body["errors"]]
    assert code in codes, codes
    if field:
        assert field in [error["field"] for error in body["errors"]]


def test_customer_not_found_or_other_company_is_422(seller, world, fakes) -> None:
    assert_error(create(seller, world, company_customer_id=uuid4()), 422, "CUSTOMER_NOT_FOUND", "company_customer_id")
    fakes.cr.customers[world.customer] = replace(fakes.cr.customers[world.customer], company_id=world.other_company)
    assert_error(create(seller, world), 422, "CUSTOMER_NOT_FOUND")


@pytest.mark.parametrize("status", ["INACTIVE", "BLOCKED"])
def test_customer_not_active_is_409(seller, world, fakes, status) -> None:
    fakes.cr.customers[world.customer] = replace(fakes.cr.customers[world.customer], status=status)
    assert_error(create(seller, world), 409, "CUSTOMER_NOT_ELIGIBLE", "company_customer_id")


def test_person_identity_not_found_is_422_and_without_identification_is_409(seller, world, fakes) -> None:
    """C-01: persona inexistente → 422; sin tipo o número → 409."""
    original = fakes.party.persons.pop(world.person)
    assert_error(create(seller, world), 422, "PERSON_IDENTITY_NOT_FOUND")
    fakes.party.persons[world.person] = replace(original, identification_number=None)
    assert_error(create(seller, world), 409, "CUSTOMER_IDENTIFICATION_MISSING")
    fakes.party.persons[world.person] = replace(original, identification_type=None)
    assert_error(create(seller, world), 409, "CUSTOMER_IDENTIFICATION_MISSING")


def test_organization_identity_not_found_is_422(seller, world, fakes) -> None:
    fakes.party.organizations.pop(world.organization)
    assert_error(create(seller, world, company_customer_id=world.customer_org), 422, "ORGANIZATION_IDENTITY_NOT_FOUND")


def test_party_identity_unavailable_is_503(seller, world, fakes) -> None:
    fakes.party.availability.down = True
    response = create(seller, world)
    assert response.status_code == 503 and response.json()["dependency"] == "party-identity"


def test_branch_of_other_company_is_422(seller, world, fakes) -> None:
    fakes.oc.branches[world.branch] = replace(fakes.oc.branches[world.branch], company_id=world.other_company)
    response = create(seller, world)
    # El acceso operativo ve una sucursal de otra empresa: no es miembro allí → 404.
    assert response.status_code in (404, 422)


def test_product_not_found_is_422(seller, world) -> None:
    assert_error(create(seller, world, line(uuid4())), 422, "COMPANY_PRODUCT_NOT_FOUND", "lines[0].company_product_id")


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"status": "INACTIVE"}, "PRODUCT_INACTIVE"),
        ({"is_sellable": False}, "PRODUCT_NOT_SELLABLE"),
        ({"inventory_control_enabled": False}, "PRODUCT_NOT_INVENTORY_CONTROLLED"),
    ],
)
def test_product_not_eligible_is_409(seller, world, fakes, test_engine, change, code) -> None:
    fakes.cr.products[world.product] = replace(fakes.cr.products[world.product], **change)
    response = create(seller, world, line(world.product_2), line(world.product))
    assert_error(response, 409, code)
    assert response.json()["errors"][0]["line_number"] == 2
    assert count_rows(test_engine, "sales") == 0


def test_presentation_of_other_product_is_422(seller, world) -> None:
    response = create(seller, world, line(world.product_2, company_product_presentation_id=world.presentation))
    assert_error(response, 422, "PRESENTATION_OF_OTHER_PRODUCT", "lines[0].company_product_presentation_id")


@pytest.mark.parametrize(
    ("change", "code"), [({"status": "INACTIVE"}, "PRESENTATION_INACTIVE"), ({"is_sellable": False}, "PRESENTATION_NOT_SELLABLE")]
)
def test_presentation_not_eligible_is_409(seller, world, fakes, change, code) -> None:
    fakes.cr.presentations[world.presentation] = replace(fakes.cr.presentations[world.presentation], **change)
    assert_error(create(seller, world, line(world.product, company_product_presentation_id=world.presentation)), 409, code)


def test_422_is_reported_before_409(seller, world, fakes) -> None:
    fakes.cr.customers[world.customer] = replace(fakes.cr.customers[world.customer], status="INACTIVE")
    response = create(seller, world, line(uuid4()))
    assert_error(response, 422, "COMPANY_PRODUCT_NOT_FOUND")


@pytest.mark.parametrize("dependency", ["oc", "cr", "catalog"])
def test_dependency_unavailable_is_503(seller, world, fakes, test_engine, dependency) -> None:
    getattr(fakes, dependency).availability.down = True
    response = create(seller, world, line(world.product))
    assert response.status_code == 503
    assert response.json()["code"] == "SALES.DEPENDENCY_UNAVAILABLE"
    assert count_rows(test_engine, "sales") == 0
