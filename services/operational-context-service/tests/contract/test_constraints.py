"""Restricciones de la base (FR-065, FR-066, Principio II) y prueba obligatoria 14."""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

EXPECTED_CONSTRAINTS = {
    "pk_companies",
    "pk_branches",
    "uq_companies_organization_identity_id",
    "uq_branches_company_id_code",
    "fk_branches_company_id_companies",
    "ck_companies_status",
    "ck_companies_coordinates_pair",
    "ck_companies_latitude_range",
    "ck_companies_longitude_range",
    "ck_companies_geography_parent",
    "ck_companies_default_currency_format",
    "ck_companies_timezone_not_blank",
    "ck_branches_status",
    "ck_branches_coordinates_pair",
    "ck_branches_latitude_range",
    "ck_branches_longitude_range",
    "ck_branches_geography_parent",
    "ck_branches_code_normalized",
    "ck_branches_timezone_not_blank",
}

EXPECTED_INDEXES = {
    "ix_companies_status",
    "ix_companies_country_id",
    "ix_companies_city_id",
    "ix_branches_company_id_status",
    "ix_branches_city_id",
}


def _insert_company(connection, **overrides):
    values = {
        "id": uuid4(),
        "organization_identity_id": uuid4(),
        "version": 1,
        "created_by": "test",
        "updated_by": "test",
    }
    values.update(overrides)
    columns = ", ".join(values)
    params = ", ".join(f":{key}" for key in values)
    connection.execute(text(f"INSERT INTO companies ({columns}) VALUES ({params})"), values)
    return values["id"]


def _insert_branch(connection, company_id, **overrides):
    values = {
        "id": uuid4(),
        "company_id": company_id,
        "code": "B-01",
        "name": "Sucursal",
        "version": 1,
        "created_by": "test",
        "updated_by": "test",
    }
    values.update(overrides)
    columns = ", ".join(values)
    params = ", ".join(f":{key}" for key in values)
    connection.execute(text(f"INSERT INTO branches ({columns}) VALUES ({params})"), values)
    return values["id"]


@pytest.fixture
def connection(test_engine, clean_database):
    with test_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


def _violates(connection, constraint, action):
    savepoint = connection.begin_nested()
    with pytest.raises(IntegrityError) as error:
        action()
    savepoint.rollback()
    assert error.value.orig.diag.constraint_name == constraint


def test_named_constraints_exist(connection):
    names = set(
        connection.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid IN ('companies'::regclass, 'branches'::regclass)"
            )
        ).scalars()
    )

    assert names == EXPECTED_CONSTRAINTS


def test_named_indexes_exist(connection):
    names = set(
        connection.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename IN ('companies', 'branches')")
        ).scalars()
    )

    assert EXPECTED_INDEXES <= names


def test_only_foreign_key_is_internal(connection):
    """Prueba obligatoria 14: ninguna FK hacia otros servicios; REF sin FK."""
    rows = connection.execute(
        text(
            "SELECT conname, conrelid::regclass::text AS source, confrelid::regclass::text AS target, "
            "(SELECT array_agg(attname) FROM pg_attribute "
            " WHERE attrelid = conrelid AND attnum = ANY(conkey)) AS columns "
            "FROM pg_constraint WHERE contype = 'f'"
        )
    ).mappings().all()

    assert [(row["conname"], row["source"], row["target"]) for row in rows] == [
        ("fk_branches_company_id_companies", "branches", "companies"),
    ]
    referenced_columns = {column for row in rows for column in row["columns"]}
    for external in ("organization_identity_id", "country_id", "administrative_division_id", "city_id"):
        assert external not in referenced_columns


def test_organization_identity_is_unique(connection):
    organization_id = uuid4()
    _insert_company(connection, organization_identity_id=organization_id)

    _violates(
        connection,
        "uq_companies_organization_identity_id",
        lambda: _insert_company(connection, organization_identity_id=organization_id),
    )


def test_branch_code_is_unique_per_company(connection):
    company_a = _insert_company(connection)
    company_b = _insert_company(connection)
    _insert_branch(connection, company_a, code="X-1")
    _insert_branch(connection, company_b, code="X-1")

    _violates(
        connection,
        "uq_branches_company_id_code",
        lambda: _insert_branch(connection, company_a, code="X-1"),
    )


def test_delete_company_with_branches_is_restricted(connection):
    """RC-08: la FK ON DELETE RESTRICT protege también contra borrados manuales."""
    company_id = _insert_company(connection)
    _insert_branch(connection, company_id)

    _violates(
        connection,
        "fk_branches_company_id_companies",
        lambda: connection.execute(text("DELETE FROM companies WHERE id = :id"), {"id": company_id}),
    )


@pytest.mark.parametrize(
    ("constraint", "overrides"),
    [
        ("ck_companies_status", {"status": "DELETED"}),
        ("ck_companies_coordinates_pair", {"latitude": 6.2}),
        ("ck_companies_latitude_range", {"latitude": 91, "longitude": 0}),
        ("ck_companies_longitude_range", {"latitude": 0, "longitude": 181}),
        ("ck_companies_geography_parent", {"city_id": uuid4()}),
        ("ck_companies_default_currency_format", {"default_currency": "co1"}),
        ("ck_companies_timezone_not_blank", {"timezone": "  "}),
    ],
)
def test_company_checks(connection, constraint, overrides):
    _violates(connection, constraint, lambda: _insert_company(connection, **overrides))


@pytest.mark.parametrize(
    ("constraint", "overrides"),
    [
        ("ck_branches_status", {"status": "CLOSED"}),
        ("ck_branches_code_normalized", {"code": "b-01"}),
        ("ck_branches_code_normalized", {"code": ""}),
        ("ck_branches_coordinates_pair", {"longitude": -75.5}),
        ("ck_branches_latitude_range", {"latitude": -91, "longitude": 0}),
        ("ck_branches_longitude_range", {"latitude": 0, "longitude": -181}),
        ("ck_branches_geography_parent", {"administrative_division_id": uuid4()}),
        ("ck_branches_timezone_not_blank", {"timezone": ""}),
    ],
)
def test_branch_checks(connection, constraint, overrides):
    company_id = _insert_company(connection)

    _violates(connection, constraint, lambda: _insert_branch(connection, company_id, **overrides))
