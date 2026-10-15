"""Semántica `422`/`409` de las referencias (P-03, P-01; FR-002, FR-005, FR-012; T030).

`422`: no existe, es de otra empresa, no puede resolverse o es incoherente.
`409`: existe, pero su estado o configuración impide usarla.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from uuid import uuid4

import pytest

from tests.conftest import base, count_rows, line, purchase_body


def create(buyer, world, *lines, **header):
    return buyer.post(f"{base(world)}/purchases", json=purchase_body(world, *lines, **header))


def assert_error(response, status: int, code: str, field: str | None = None) -> None:
    assert response.status_code == status, response.text
    body = response.json()
    expected = "PURCHASE.VALIDATION_ERROR" if status == 422 else "PURCHASE.REFERENCES_NOT_ELIGIBLE"
    assert body["code"] == expected
    codes = [error["code"] for error in body["errors"]]
    assert code in codes, codes
    if field:
        assert field in [error["field"] for error in body["errors"]]


def test_supplier_not_found_or_other_company_is_422(buyer, world, fakes) -> None:
    assert_error(create(buyer, world, company_supplier_id=uuid4()), 422, "SUPPLIER_NOT_FOUND", "company_supplier_id")
    fakes.cr.suppliers[world.supplier] = replace(fakes.cr.suppliers[world.supplier], company_id=world.other_company)
    assert_error(create(buyer, world), 422, "SUPPLIER_NOT_FOUND")


@pytest.mark.parametrize("status", ["BLOCKED", "INACTIVE"])
def test_supplier_not_active_is_409(buyer, world, fakes, status) -> None:
    fakes.cr.suppliers[world.supplier] = replace(fakes.cr.suppliers[world.supplier], status=status)
    assert_error(create(buyer, world), 409, "SUPPLIER_NOT_ELIGIBLE", "company_supplier_id")


def test_supplier_organization_not_found_is_422(buyer, world, fakes) -> None:
    """D-08: organización inexistente en Party Identity → `422`."""
    fakes.party.organizations.clear()
    assert_error(create(buyer, world), 422, "ORGANIZATION_IDENTITY_NOT_FOUND", "company_supplier_id")


@pytest.mark.parametrize("change", [{"identification_number": None}, {"identification_type": None}])
def test_supplier_organization_without_identification_is_409(buyer, world, fakes, change) -> None:
    """D-08: organización existente sin los datos obligatorios para la compra → `409`."""
    organization = fakes.party.organizations[world.organization]
    fakes.party.organizations[world.organization] = replace(organization, **change)
    assert_error(create(buyer, world), 409, "ORGANIZATION_IDENTIFICATION_MISSING", "company_supplier_id")


def test_party_identity_and_payment_reference_unavailable_are_503(buyer, world, fakes) -> None:
    fakes.party.availability.down = True
    response = create(buyer, world)
    assert response.status_code == 503 and response.json()["dependency"] == "party-identity"
    fakes.party.availability.down = False
    fakes.pr.availability.down = True
    response = create(buyer, world, supplier_payment_condition_id=world.condition)
    assert response.status_code == 503 and response.json()["dependency"] == "payment-reference"


def test_product_not_found_is_422(buyer, world, fakes) -> None:
    assert_error(create(buyer, world, line(uuid4())), 422, "COMPANY_PRODUCT_NOT_FOUND", "lines[0].company_product_id")
    fakes.cr.products[world.product] = replace(fakes.cr.products[world.product], company_id=world.other_company)
    assert_error(create(buyer, world, line(world.product)), 422, "COMPANY_PRODUCT_NOT_FOUND")


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"status": "INACTIVE"}, "PRODUCT_INACTIVE"),
        ({"is_purchasable": False}, "PRODUCT_NOT_PURCHASABLE"),
        ({"inventory_control_enabled": False}, "PRODUCT_NOT_INVENTORY_CONTROLLED"),
    ],
)
def test_product_existing_but_not_fit_is_409(buyer, world, fakes, change, code) -> None:
    fakes.cr.products[world.product] = replace(fakes.cr.products[world.product], **change)
    assert_error(create(buyer, world, line(world.product)), 409, code, "lines[0].company_product_id")


def test_product_without_inventory_control_is_409(buyer, world) -> None:
    """P-01: toda compra confirmada genera entrada en Inventory."""
    response = create(buyer, world, line(world.product_no_inventory))
    assert_error(response, 409, "PRODUCT_NOT_INVENTORY_CONTROLLED")
    assert response.json()["errors"][0]["line_number"] == 1


def test_presentation_rules(buyer, world, fakes) -> None:
    assert_error(
        create(buyer, world, line(world.product, company_product_presentation_id=uuid4())),
        422, "PRESENTATION_NOT_FOUND", "lines[0].company_product_presentation_id",
    )
    assert_error(
        create(buyer, world, line(world.product_2, company_product_presentation_id=world.presentation)),
        422, "PRESENTATION_OF_OTHER_PRODUCT",
    )
    fakes.cr.presentations[world.presentation] = replace(fakes.cr.presentations[world.presentation], is_purchasable=False)
    assert_error(create(buyer, world, line(world.product, company_product_presentation_id=world.presentation)), 409, "PRESENTATION_NOT_PURCHASABLE")
    fakes.cr.presentations[world.presentation] = replace(fakes.cr.presentations[world.presentation], status="INACTIVE", is_purchasable=True)
    assert_error(create(buyer, world, line(world.product, company_product_presentation_id=world.presentation)), 409, "PRESENTATION_INACTIVE")


def test_supplier_product_rules(buyer, world, fakes) -> None:
    assert_error(create(buyer, world, line(world.product, supplier_product_id=uuid4())), 422, "SUPPLIER_PRODUCT_NOT_FOUND")
    assert_error(create(buyer, world, line(world.product_2, supplier_product_id=world.supplier_product)), 422, "SUPPLIER_PRODUCT_MISMATCH")
    sp = fakes.cr.supplier_products[world.supplier_product]
    fakes.cr.supplier_products[world.supplier_product] = replace(sp, company_supplier_id=uuid4())
    assert_error(create(buyer, world, line(world.product, supplier_product_id=world.supplier_product)), 422, "SUPPLIER_PRODUCT_MISMATCH")
    fakes.cr.supplier_products[world.supplier_product] = replace(sp, status="INACTIVE")
    assert_error(create(buyer, world, line(world.product, supplier_product_id=world.supplier_product)), 409, "SUPPLIER_PRODUCT_INACTIVE")


def test_payment_condition_rules(buyer, world, fakes) -> None:
    condition = fakes.cr.conditions[world.condition]
    assert_error(create(buyer, world, supplier_payment_condition_id=uuid4()), 422, "PAYMENT_CONDITION_NOT_FOUND")
    fakes.cr.conditions[world.condition] = replace(condition, company_supplier_id=uuid4())
    assert_error(create(buyer, world, supplier_payment_condition_id=world.condition), 422, "PAYMENT_CONDITION_OF_OTHER_SUPPLIER")
    fakes.cr.conditions[world.condition] = replace(condition, status="INACTIVE")
    assert_error(create(buyer, world, supplier_payment_condition_id=world.condition), 409, "PAYMENT_CONDITION_INACTIVE")
    fakes.cr.conditions[world.condition] = replace(condition, valid_to=date.today() - timedelta(days=1))
    assert_error(create(buyer, world, supplier_payment_condition_id=world.condition), 409, "PAYMENT_CONDITION_NOT_VALID_ON_DATE")
    fakes.cr.conditions[world.condition] = replace(condition, currency_code="USD")
    assert_error(create(buyer, world, supplier_payment_condition_id=world.condition), 409, "PAYMENT_CONDITION_CURRENCY_MISMATCH")
    fakes.cr.conditions[world.condition] = condition
    fakes.pr.types[world.cash_type] = replace(fakes.pr.types[world.cash_type], status="INACTIVE")
    assert_error(create(buyer, world, supplier_payment_condition_id=world.condition), 409, "PAYMENT_CONDITION_TYPE_INACTIVE")
    fakes.pr.types.clear()  # D-08: tipo inexistente en Payment Reference → `422`
    assert_error(create(buyer, world, supplier_payment_condition_id=world.condition), 422, "PAYMENT_CONDITION_TYPE_NOT_FOUND")


def test_branch_rules(buyer, world, fakes) -> None:
    fakes.oc.branches[world.branch] = replace(fakes.oc.branches[world.branch], status="INACTIVE")
    response = create(buyer, world)  # Operational Context niega el acceso a una sucursal inactiva
    assert response.status_code == 403 and response.json()["code"] == "PURCHASE.BRANCH_ACCESS_DENIED"
    fakes.oc.branches[world.branch] = replace(fakes.oc.branches[world.branch], status="ACTIVE")
    response = create(buyer, world, branch_id=uuid4())
    assert response.status_code == 404  # sucursal desconocida: no hay membresía que evaluar
    fakes.oc.companies[world.company] = replace(fakes.oc.companies[world.company], status="INACTIVE")
    assert_error(create(buyer, world), 409, "COMPANY_INACTIVE")


def test_invalid_reported_before_not_eligible(buyer, world, fakes) -> None:
    fakes.cr.suppliers[world.supplier] = replace(fakes.cr.suppliers[world.supplier], status="BLOCKED")
    response = create(buyer, world, line(uuid4()))
    assert response.status_code == 422


def test_rejections_persist_nothing(buyer, world, test_engine) -> None:
    create(buyer, world, line(world.product_no_inventory))
    create(buyer, world, company_supplier_id=uuid4())
    assert count_rows(test_engine, "purchases") == 0
    assert count_rows(test_engine, "audit_outbox") == 0
