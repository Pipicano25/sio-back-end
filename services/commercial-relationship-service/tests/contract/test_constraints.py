"""Restricciones de la base por nombre (RC-04, RC-07, RC-08; data-model.md)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

AUDIT = "'sub-test', 'sub-test'"


def _insert_product(session, *, company_id, global_product_id=None, code="P-1", **overrides):
    values = {
        "id": uuid4(),
        "company_id": company_id,
        "global_product_id": global_product_id or uuid4(),
        "internal_code": code,
        "display_name": "Producto",
        "currency_code": "COP",
        "sale_price": 0,
        "reference_cost": 0,
        "inventory_control_enabled": True,
        "lot_tracking_enabled": False,
        "expiration_tracking_enabled": False,
        "status": "ACTIVE",
    }
    values.update(overrides)
    columns = ", ".join(values)
    params = ", ".join(f":{name}" for name in values)
    session.execute(
        text(f"INSERT INTO company_products ({columns}, created_by, updated_by) VALUES ({params}, {AUDIT})"),
        values,
    )
    session.commit()


def _insert_customer(session, *, company_id, code="C-1", **overrides):
    values = {
        "id": uuid4(),
        "company_id": company_id,
        "customer_kind": "PERSON",
        "person_identity_id": uuid4(),
        "organization_identity_id": None,
        "internal_code": code,
        "display_name": "Cliente",
        "preferred_contact_person_id": None,
        "status": "ACTIVE",
    }
    values.update(overrides)
    columns = ", ".join(values)
    params = ", ".join(f":{name}" for name in values)
    session.execute(
        text(f"INSERT INTO company_customers ({columns}, created_by, updated_by) VALUES ({params}, {AUDIT})"),
        values,
    )
    session.commit()


def _insert_supplier(session, *, company_id, code="S-1", **overrides):
    values = {
        "id": uuid4(),
        "company_id": company_id,
        "organization_identity_id": uuid4(),
        "internal_code": code,
        "display_name": "Proveedor",
        "status": "ACTIVE",
        "block_reason": None,
    }
    values.update(overrides)
    columns = ", ".join(values)
    params = ", ".join(f":{name}" for name in values)
    session.execute(
        text(f"INSERT INTO company_suppliers ({columns}, created_by, updated_by) VALUES ({params}, {AUDIT})"),
        values,
    )
    session.commit()


def _violates(session, constraint: str, action) -> None:
    with pytest.raises(IntegrityError) as error:
        action()
    session.rollback()
    assert error.value.orig.diag.constraint_name == constraint


# ------------------------------------------------------------------ productos


def test_product_unique_adoption(db_session):
    company, product = uuid4(), uuid4()
    _insert_product(db_session, company_id=company, global_product_id=product, code="A")
    _violates(
        db_session,
        "uq_company_products_company_id_global_product_id",
        lambda: _insert_product(db_session, company_id=company, global_product_id=product, code="B"),
    )
    # Otra empresa puede adoptar el mismo producto global.
    _insert_product(db_session, company_id=uuid4(), global_product_id=product, code="A")


def test_product_internal_code_case_insensitive(db_session):
    company = uuid4()
    _insert_product(db_session, company_id=company, code="ABC-1")
    _violates(
        db_session,
        "uq_company_products_company_id_internal_code_ci",
        lambda: _insert_product(db_session, company_id=company, code="abc-1"),
    )
    _insert_product(db_session, company_id=uuid4(), code="abc-1")


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"sale_price": -1}, "ck_company_products_sale_price_non_negative"),
        ({"reference_cost": -0.0001}, "ck_company_products_reference_cost_non_negative"),
        ({"currency_code": "cop"}, "ck_company_products_currency_code_format"),
        (
            {"inventory_control_enabled": False, "lot_tracking_enabled": True},
            "ck_company_products_lot_requires_inventory",
        ),
        (
            {"lot_tracking_enabled": False, "expiration_tracking_enabled": True},
            "ck_company_products_expiration_requires_lot",
        ),
        ({"internal_code": " X"}, "ck_company_products_internal_code_not_blank"),
        ({"display_name": "   "}, "ck_company_products_display_name_not_blank"),
        ({"status": "BLOCKED"}, "ck_company_products_status"),
    ],
)
def test_product_checks(db_session, overrides, constraint):
    _violates(db_session, constraint, lambda: _insert_product(db_session, company_id=uuid4(), **overrides))


# ------------------------------------------------------------------- clientes


@pytest.mark.parametrize(
    "overrides",
    [
        {"customer_kind": "PERSON", "person_identity_id": None, "organization_identity_id": None},
        {"customer_kind": "PERSON", "organization_identity_id": uuid4()},
        {"customer_kind": "ORGANIZATION", "person_identity_id": None, "organization_identity_id": None},
        {"customer_kind": "ORGANIZATION", "organization_identity_id": uuid4()},
    ],
)
def test_customer_identity_by_kind(db_session, overrides):
    _violates(
        db_session,
        "ck_company_customers_identity_by_kind",
        lambda: _insert_customer(db_session, company_id=uuid4(), **overrides),
    )


def test_customer_kind_and_contact_checks(db_session):
    # Un tipo fuera de PERSON/ORGANIZATION incumple también identity_by_kind, que
    # PostgreSQL puede evaluar antes: se exige que la base lo rechace por una de las dos.
    with pytest.raises(IntegrityError) as error:
        _insert_customer(db_session, company_id=uuid4(), customer_kind="OTHER")
    db_session.rollback()
    assert error.value.orig.diag.constraint_name in {
        "ck_company_customers_kind",
        "ck_company_customers_identity_by_kind",
    }

    _violates(
        db_session,
        "ck_company_customers_contact_only_organization",
        lambda: _insert_customer(db_session, company_id=uuid4(), preferred_contact_person_id=uuid4()),
    )


def test_customer_unique_identity_and_code(db_session):
    company, person, organization = uuid4(), uuid4(), uuid4()
    _insert_customer(db_session, company_id=company, person_identity_id=person, code="C-1")
    _violates(
        db_session,
        "uq_company_customers_company_id_person_identity_id",
        lambda: _insert_customer(db_session, company_id=company, person_identity_id=person, code="C-2"),
    )
    _insert_customer(
        db_session,
        company_id=company,
        customer_kind="ORGANIZATION",
        person_identity_id=None,
        organization_identity_id=organization,
        code="C-3",
    )
    _violates(
        db_session,
        "uq_company_customers_company_id_organization_identity_id",
        lambda: _insert_customer(
            db_session,
            company_id=company,
            customer_kind="ORGANIZATION",
            person_identity_id=None,
            organization_identity_id=organization,
            code="C-4",
        ),
    )
    _violates(
        db_session,
        "uq_company_customers_company_id_internal_code_ci",
        lambda: _insert_customer(db_session, company_id=company, code="c-1"),
    )


# ---------------------------------------------------------------- proveedores


def test_supplier_unique_organization_and_code(db_session):
    company, organization = uuid4(), uuid4()
    _insert_supplier(db_session, company_id=company, organization_identity_id=organization, code="S-1")
    _violates(
        db_session,
        "uq_company_suppliers_company_id_organization_identity_id",
        lambda: _insert_supplier(db_session, company_id=company, organization_identity_id=organization, code="S-2"),
    )
    _violates(
        db_session,
        "uq_company_suppliers_company_id_internal_code_ci",
        lambda: _insert_supplier(db_session, company_id=company, code="s-1"),
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "BLOCKED", "block_reason": None},
        {"status": "BLOCKED", "block_reason": "   "},
        {"status": "ACTIVE", "block_reason": "motivo"},
        {"status": "INACTIVE", "block_reason": "motivo"},
    ],
)
def test_supplier_block_reason_consistency(db_session, overrides):
    _violates(
        db_session,
        "ck_company_suppliers_block_reason_consistency",
        lambda: _insert_supplier(db_session, company_id=uuid4(), **overrides),
    )


def test_supplier_status_check_and_valid_blocked(db_session):
    _violates(
        db_session,
        "ck_company_suppliers_status",
        lambda: _insert_supplier(db_session, company_id=uuid4(), status="DELETED"),
    )
    _insert_supplier(db_session, company_id=uuid4(), status="BLOCKED", block_reason="Incumplimiento")
