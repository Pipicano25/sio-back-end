"""Restricciones de la Fase B por nombre (T004; RC-04, RC-05, RC-06, RC-09, RC-15; data-model.md de la 010).

Se inserta por SQL directo para probar la base sin pasar por la aplicación:
FK compuestas (misma empresa y mismo producto), índices únicos y parciales,
`CHECK`, la exclusión de vigencias y la ausencia de columnas de datos de otros
servicios (G1).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

AUDIT = {"created_by": "sub-test", "updated_by": "sub-test"}


def _insert(session, table: str, **values):
    values = {"id": uuid4(), **values, **AUDIT}
    columns = ", ".join(values)
    params = ", ".join(f":{name}" for name in values)
    session.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({params})"), values)
    session.commit()
    return values["id"]


def _violates(session, constraint: str, table: str, **values) -> None:
    with pytest.raises(IntegrityError) as error:
        _insert(session, table, **values)
    session.rollback()
    assert error.value.orig.diag.constraint_name == constraint


def _product(session, company_id, **overrides):
    return _insert(
        session,
        "company_products",
        company_id=company_id,
        global_product_id=uuid4(),
        internal_code=f"P-{uuid4().hex[:8]}",
        display_name="Producto",
        currency_code="COP",
        **overrides,
    )


def _supplier(session, company_id, **overrides):
    return _insert(
        session,
        "company_suppliers",
        company_id=company_id,
        organization_identity_id=uuid4(),
        internal_code=f"S-{uuid4().hex[:8]}",
        display_name="Proveedor",
        **overrides,
    )


def _presentation(session, company_id, product_id, **overrides):
    values = {"company_id": company_id, "company_product_id": product_id, "global_product_presentation_id": uuid4()}
    return _insert(session, "company_product_presentations", **{**values, **overrides})


def _price_list(session, company_id, **overrides):
    values = {"company_id": company_id, "code": f"L-{uuid4().hex[:8]}", "name": "Lista", "currency_code": "COP"}
    return _insert(session, "price_lists", **{**values, **overrides})


@pytest.fixture
def base(db_session):
    company = uuid4()
    product = _product(db_session, company)
    return {"company": company, "product": product, "session": db_session}


# ------------------------------------------------------------- FK compuestas


def test_presentation_requires_product_of_same_company(base):
    _violates(
        base["session"],
        "fk_company_product_presentations_company_product",
        "company_product_presentations",
        company_id=uuid4(),
        company_product_id=base["product"],
        global_product_presentation_id=uuid4(),
    )


def test_supplier_product_foreign_keys(base):
    session, company, product = base["session"], base["company"], base["product"]
    supplier = _supplier(session, company)
    other_product = _product(session, company)
    presentation_of_other = _presentation(session, company, other_product)
    common = {"purchase_unit_id": uuid4(), "currency_code": "COP"}

    _violates(
        session, "fk_supplier_products_company_supplier", "supplier_products",
        company_id=company, company_supplier_id=_supplier(session, uuid4()), company_product_id=product, **common,
    )
    _violates(
        session, "fk_supplier_products_company_product", "supplier_products",
        company_id=company, company_supplier_id=supplier, company_product_id=_product(session, uuid4()), **common,
    )
    _violates(
        session, "fk_supplier_products_presentation", "supplier_products",
        company_id=company, company_supplier_id=supplier, company_product_id=product,
        company_product_presentation_id=presentation_of_other, **common,
    )
    # MATCH SIMPLE: sin presentación no se verifica la FK de presentación.
    _insert(session, "supplier_products", company_id=company, company_supplier_id=supplier, company_product_id=product, **common)


def test_payment_condition_requires_supplier_of_same_company(base):
    _violates(
        base["session"], "fk_supplier_payment_conditions_company_supplier", "supplier_payment_conditions",
        company_id=base["company"], company_supplier_id=_supplier(base["session"], uuid4()),
        payment_condition_type_id=uuid4(), currency_code="COP",
    )


def test_price_list_item_foreign_keys(base):
    session, company, product = base["session"], base["company"], base["product"]
    price_list = _price_list(session, company)
    presentation_of_other = _presentation(session, company, _product(session, company))

    _violates(
        session, "fk_price_list_items_price_list", "price_list_items",
        company_id=company, price_list_id=_price_list(session, uuid4()), company_product_id=product, unit_price=1,
    )
    _violates(
        session, "fk_price_list_items_company_product", "price_list_items",
        company_id=company, price_list_id=price_list, company_product_id=_product(session, uuid4()), unit_price=1,
    )
    _violates(
        session, "fk_price_list_items_presentation", "price_list_items",
        company_id=company, price_list_id=price_list, company_product_id=product,
        company_product_presentation_id=presentation_of_other, unit_price=1,
    )


# --------------------------------------------------------------- unicidades


def test_presentation_uniqueness(base):
    session, company, product = base["session"], base["company"], base["product"]
    global_presentation = uuid4()
    _presentation(session, company, product, global_product_presentation_id=global_presentation, sku="CJ12", internal_code="INT-1")

    _violates(
        session, "uq_company_product_presentations_product_global_presentation", "company_product_presentations",
        company_id=company, company_product_id=product, global_product_presentation_id=global_presentation,
    )
    _violates(
        session, "uq_company_product_presentations_company_id_sku_ci", "company_product_presentations",
        company_id=company, company_product_id=product, global_product_presentation_id=uuid4(), sku="cj12",
    )
    _violates(
        session, "uq_company_product_presentations_company_id_internal_code_ci", "company_product_presentations",
        company_id=company, company_product_id=product, global_product_presentation_id=uuid4(), internal_code="int-1",
    )
    # Varios sin SKU ni código interno: los nulos no chocan.
    _presentation(session, company, product)
    _presentation(session, company, product)


@pytest.mark.parametrize(
    ("table", "flag", "constraint"),
    [
        ("company_product_presentations", "is_default_purchase", "uq_company_product_presentations_default_purchase"),
        ("company_product_presentations", "is_default_sale", "uq_company_product_presentations_default_sale"),
    ],
)
def test_presentation_default_is_unique_among_active(base, table, flag, constraint):
    session, company, product = base["session"], base["company"], base["product"]
    _presentation(session, company, product, **{flag: True})
    _violates(session, constraint, table, company_id=company, company_product_id=product,
              global_product_presentation_id=uuid4(), **{flag: True})


def test_supplier_product_active_relation_and_preferred(base):
    session, company, product = base["session"], base["company"], base["product"]
    supplier = _supplier(session, company)
    presentation = _presentation(session, company, product)
    common = {"company_id": company, "company_supplier_id": supplier, "company_product_id": product,
              "purchase_unit_id": uuid4(), "currency_code": "COP"}

    _insert(session, "supplier_products", **common, is_preferred=True)
    _insert(session, "supplier_products", **common, company_product_presentation_id=presentation)
    # La ausencia de presentación cuenta como un valor (aclaración 3).
    _violates(session, "uq_supplier_products_active_relation", "supplier_products", **common)
    # Las INACTIVE no cuentan.
    _insert(session, "supplier_products", **common, status="INACTIVE")
    _violates(
        session, "uq_supplier_products_preferred", "supplier_products",
        **{**common, "company_supplier_id": _supplier(session, company)}, is_preferred=True,
    )


def test_payment_condition_default_per_currency(base):
    session, company = base["session"], base["company"]
    supplier = _supplier(session, company)
    common = {"company_id": company, "company_supplier_id": supplier, "payment_condition_type_id": uuid4()}

    _insert(session, "supplier_payment_conditions", **common, currency_code="COP", is_default=True)
    _insert(session, "supplier_payment_conditions", **common, currency_code="USD", is_default=True)
    _insert(session, "supplier_payment_conditions", **common, currency_code="COP")
    _violates(
        session, "uq_supplier_payment_conditions_default", "supplier_payment_conditions",
        **common, currency_code="COP", is_default=True,
    )


def test_price_list_code_and_default(base):
    session, company = base["session"], base["company"]
    _price_list(session, company, code="MINORISTA", is_default=True)
    _violates(session, "uq_price_lists_company_id_code_ci", "price_lists",
              company_id=company, code="minorista", name="Otra", currency_code="COP")
    _violates(session, "uq_price_lists_default", "price_lists",
              company_id=company, code="MAYORISTA", name="Mayorista", currency_code="COP", is_default=True)
    _price_list(session, company, code="EXPORT", currency_code="USD", is_default=True)


# ------------------------------------------------------------------- CHECK


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"is_purchasable": False, "is_default_purchase": True}, "ck_company_product_presentations_default_purchase_purchasable"),
        ({"is_sellable": False, "is_default_sale": True}, "ck_company_product_presentations_default_sale_sellable"),
        ({"status": "INACTIVE", "is_default_sale": True}, "ck_company_product_presentations_default_requires_active"),
        ({"sku": " CJ "}, "ck_company_product_presentations_codes_not_blank"),
        ({"status": "BLOCKED"}, "ck_company_product_presentations_status"),
    ],
)
def test_presentation_checks(base, overrides, constraint):
    _violates(base["session"], constraint, "company_product_presentations", company_id=base["company"],
              company_product_id=base["product"], global_product_presentation_id=uuid4(), **overrides)


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"pack_quantity": 0}, "ck_supplier_products_quantities"),
        ({"minimum_order_quantity": -1}, "ck_supplier_products_quantities"),
        ({"negotiated_unit_cost": -1}, "ck_supplier_products_non_negative"),
        ({"expected_supplier_lead_time_hours": -1}, "ck_supplier_products_non_negative"),
        ({"priority": -1}, "ck_supplier_products_non_negative"),
        ({"status": "INACTIVE", "is_preferred": True}, "ck_supplier_products_preferred_requires_active"),
        ({"currency_code": "co"}, "ck_supplier_products_currency_code_format"),
    ],
)
def test_supplier_product_checks(base, overrides, constraint):
    session = base["session"]
    values = {"company_id": base["company"], "company_supplier_id": _supplier(session, base["company"]),
              "company_product_id": base["product"], "purchase_unit_id": uuid4(), "currency_code": "COP"}
    values.update(overrides)
    _violates(session, constraint, "supplier_products", **values)


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"payment_terms_days": 3651}, "ck_supplier_payment_conditions_terms_range"),
        ({"payment_terms_days": -1}, "ck_supplier_payment_conditions_terms_range"),
        ({"credit_limit": -1}, "ck_supplier_payment_conditions_amounts"),
        ({"interest_rate_percentage": 100.0001}, "ck_supplier_payment_conditions_amounts"),
        ({"cash_discount_percentage": -1}, "ck_supplier_payment_conditions_amounts"),
        ({"valid_from": "2026-10-05T00:00:00Z", "valid_to": "2026-10-05T00:00:00Z"}, "ck_supplier_payment_conditions_validity"),
        ({"status": "INACTIVE", "is_default": True}, "ck_supplier_payment_conditions_default_requires_active"),
    ],
)
def test_payment_condition_checks(base, overrides, constraint):
    session = base["session"]
    values = {"company_id": base["company"], "company_supplier_id": _supplier(session, base["company"]),
              "payment_condition_type_id": uuid4(), "currency_code": "COP"}
    values.update(overrides)
    _violates(session, constraint, "supplier_payment_conditions", **values)


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"valid_from": "2026-10-05T00:00:00Z", "valid_to": "2026-10-04T00:00:00Z"}, "ck_price_lists_validity"),
        ({"status": "INACTIVE", "is_default": True}, "ck_price_lists_default_requires_active"),
        ({"code": " X"}, "ck_price_lists_code_not_blank"),
        ({"name": "  "}, "ck_price_lists_name_not_blank"),
    ],
)
def test_price_list_checks(base, overrides, constraint):
    values = {"company_id": base["company"], "code": "L1", "name": "Lista", "currency_code": "COP"}
    values.update(overrides)
    _violates(base["session"], constraint, "price_lists", **values)


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"unit_price": -0.01}, "ck_price_list_items_unit_price_non_negative"),
        ({"valid_from": "2026-10-05T00:00:00Z", "valid_to": "2026-10-05T00:00:00Z"}, "ck_price_list_items_validity"),
        ({"status": "DELETED"}, "ck_price_list_items_status"),
    ],
)
def test_price_list_item_checks(base, overrides, constraint):
    session = base["session"]
    values = {"company_id": base["company"], "price_list_id": _price_list(session, base["company"]),
              "company_product_id": base["product"], "unit_price": 1}
    values.update(overrides)
    _violates(session, constraint, "price_list_items", **values)


# --------------------------------------------------------------- exclusión


def test_price_periods_exclusion(base):
    session, company, product = base["session"], base["company"], base["product"]
    price_list = _price_list(session, company)
    presentation = _presentation(session, company, product)
    common = {"company_id": company, "price_list_id": price_list, "company_product_id": product, "unit_price": 1}

    _insert(session, "price_list_items", **common, valid_from="2026-01-01T00:00:00Z", valid_to="2026-02-01T00:00:00Z")
    # Rangos [) contiguos: permitidos.
    _insert(session, "price_list_items", **common, valid_from="2026-02-01T00:00:00Z", valid_to="2026-03-01T00:00:00Z")
    # Sin fin desde marzo y otro futuro: choca.
    _insert(session, "price_list_items", **common, valid_from="2026-03-01T00:00:00Z")
    _violates(session, "ex_price_list_items_no_overlap", "price_list_items", **common, valid_from="2027-01-01T00:00:00Z")
    # Un precio INACTIVE no choca.
    _insert(session, "price_list_items", **common, valid_from="2027-01-01T00:00:00Z", status="INACTIVE")
    # La presentación es otro valor: no choca con el precio general.
    _insert(session, "price_list_items", **common, company_product_presentation_id=presentation, valid_from="2026-01-15T00:00:00Z")
    # Y la ausencia de presentación se compara como valor.
    _violates(session, "ex_price_list_items_no_overlap", "price_list_items", **common, valid_from="2026-01-15T00:00:00Z", valid_to="2026-01-20T00:00:00Z")


# ------------------------------------------------- sin datos ajenos (G1)

EXPECTED_COLUMNS = {
    "company_product_presentations": {
        "id", "company_id", "company_product_id", "global_product_presentation_id", "internal_code", "sku",
        "reference_code", "is_purchasable", "is_sellable", "is_default_purchase", "is_default_sale",
    },
    "supplier_products": {
        "id", "company_id", "company_supplier_id", "company_product_id", "company_product_presentation_id",
        "supplier_product_code", "purchase_unit_id", "minimum_order_quantity", "pack_quantity",
        "negotiated_unit_cost", "currency_code", "expected_supplier_lead_time_hours", "priority", "is_preferred",
    },
    "supplier_payment_conditions": {
        "id", "company_id", "company_supplier_id", "payment_condition_type_id", "currency_code",
        "payment_terms_days", "credit_limit", "interest_rate_percentage", "cash_discount_percentage",
        "is_default", "valid_from", "valid_to",
    },
    "price_lists": {
        "id", "company_id", "code", "name", "description", "currency_code", "is_default", "valid_from", "valid_to",
    },
    "price_list_items": {
        "id", "company_id", "price_list_id", "company_product_id", "company_product_presentation_id",
        "unit_price", "valid_from", "valid_to",
        "origin", "closure_reason", "automatic_application_id",  # spec 021 (FR-021-24)
    },
}
AUDIT_COLUMNS = {"status", "version", "created_at", "updated_at", "created_by", "updated_by"}

# Datos propiedad de otros servicios que no deben existir como columnas (Principio III).
FOREIGN_DATA_COLUMNS = {
    "supplier_payment_conditions": {"code", "name", "description", "payment_condition_type_code"},
    "company_product_presentations": {"name", "base_quantity", "packaging_type_id", "content_quantity", "gtin", "barcode"},
    "supplier_products": {"unit_name", "unit_symbol", "base_unit_id"},
}
PARTY_AND_COMPANY_COLUMNS = {
    "legal_name", "first_name", "last_name", "identification_number", "email", "phone", "address",
    "organization_identity_id", "company_name", "created_by_user_id", "is_active",
}


@pytest.mark.parametrize("table", sorted(EXPECTED_COLUMNS))
def test_tables_have_exactly_declared_columns_without_foreign_data(test_engine, table):
    columns = {column["name"] for column in inspect(test_engine).get_columns(table)}

    assert columns == EXPECTED_COLUMNS[table] | AUDIT_COLUMNS
    assert not columns & FOREIGN_DATA_COLUMNS.get(table, set())
    assert not columns & PARTY_AND_COMPANY_COLUMNS
