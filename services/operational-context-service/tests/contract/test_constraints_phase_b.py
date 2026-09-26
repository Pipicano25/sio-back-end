"""Restricciones de la base de la Fase B (data-model.md de la feature 005).

RC-04 (unicidades activas), RC-06 (misma empresa por FK compuesta), RC-08
(invariante de vigencia), RC-10 (FK `RESTRICT`), RC-14 (persona obligatoria).
"""

from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

EXPECTED_CONSTRAINTS = {
    "pk_application_users",
    "pk_user_branches",
    "pk_company_advisor_assignments",
    "uq_branches_id_company_id",
    "uq_application_users_id_company_id",
    "fk_application_users_company_id_companies",
    "ck_application_users_status",
    "ck_application_users_keycloak_user_id_not_blank",
    "ck_application_users_display_name_not_blank",
    "uq_user_branches_application_user_id_branch_id",
    "fk_user_branches_application_user_company",
    "fk_user_branches_branch_company",
    "ck_user_branches_status",
    "ck_user_branches_deactivation_consistency",
    "ck_user_branches_assigned_by_not_blank",
    "fk_company_advisor_assignments_company_id_companies",
    "ck_company_advisor_assignments_status",
    "ck_company_advisor_assignments_validity",
    "ck_company_advisor_assignments_assigned_by_not_blank",
}

EXPECTED_INDEXES = {
    "uq_application_users_company_id_person_identity_id_active",
    "uq_application_users_company_id_keycloak_user_id_active",
    "ix_application_users_keycloak_user_id_status",
    "ix_application_users_company_id_status",
    "ix_application_users_person_identity_id",
    "ix_user_branches_branch_id_status",
    "uq_company_advisor_assignments_company_id_primary_active",
    "uq_company_advisor_assignments_company_person_active",
    "ix_company_advisor_assignments_company_id_valid_from",
    "ix_company_advisor_assignments_person_identity_id",
}

AUDIT = {"version": 1, "created_by": "test", "updated_by": "test"}


def _insert(connection, table, values):
    columns = ", ".join(values)
    params = ", ".join(f":{key}" for key in values)
    connection.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({params})"), values)


def _company(connection):
    company_id = uuid4()
    _insert(connection, "companies", {"id": company_id, "organization_identity_id": uuid4(), **AUDIT})
    return company_id


def _branch(connection, company_id, code="B-01"):
    branch_id = uuid4()
    _insert(
        connection,
        "branches",
        {"id": branch_id, "company_id": company_id, "code": code, "name": "Sucursal", **AUDIT},
    )
    return branch_id


def _user(connection, company_id, **overrides):
    values = {
        "id": uuid4(),
        "company_id": company_id,
        "keycloak_user_id": "sub-" + uuid4().hex,
        "person_identity_id": uuid4(),
        "display_name": "Usuario Ficticio",
        **AUDIT,
    }
    values.update(overrides)
    _insert(connection, "application_users", values)
    return values["id"]


def _advisor(connection, company_id, **overrides):
    values = {
        "id": uuid4(),
        "company_id": company_id,
        "person_identity_id": uuid4(),
        "assigned_by": "test",
        **AUDIT,
    }
    values.update(overrides)
    _insert(connection, "company_advisor_assignments", values)
    return values["id"]


def _violates(engine, action) -> bool:
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            action(connection)
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        except IntegrityError:
            transaction.rollback()
            return True
        transaction.rollback()
        return False


@pytest.fixture
def engine(test_engine, clean_database):
    return test_engine


def test_named_constraints_and_indexes_exist(engine):
    with engine.connect() as connection:
        constraints = set(
            connection.execute(
                text(
                    "SELECT conname FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid "
                    "WHERE t.relname IN ('application_users', 'user_branches', "
                    "'company_advisor_assignments', 'branches')"
                )
            ).scalars()
        )
        indexes = set(
            connection.execute(
                text(
                    "SELECT indexname FROM pg_indexes WHERE tablename IN "
                    "('application_users', 'user_branches', 'company_advisor_assignments')"
                )
            ).scalars()
        )

    assert EXPECTED_CONSTRAINTS <= constraints
    assert EXPECTED_INDEXES <= indexes


# --------------------------------------------------------------- application_users


def test_one_active_membership_per_company_and_person(engine):
    def action(connection):
        company = _company(connection)
        person = uuid4()
        _user(connection, company, person_identity_id=person)
        _user(connection, company, person_identity_id=person)

    assert _violates(engine, action)


def test_one_active_membership_per_company_and_sub(engine):
    def action(connection):
        company = _company(connection)
        _user(connection, company, keycloak_user_id="sub-1")
        _user(connection, company, keycloak_user_id="sub-1")

    assert _violates(engine, action)


def test_inactive_memberships_do_not_block_history(engine):
    def action(connection):
        company = _company(connection)
        person = uuid4()
        _user(connection, company, person_identity_id=person, keycloak_user_id="sub-1", status="INACTIVE")
        _user(connection, company, person_identity_id=person, keycloak_user_id="sub-1", status="INACTIVE")
        _user(connection, company, person_identity_id=person, keycloak_user_id="sub-1")

    assert not _violates(engine, action)


def test_same_person_and_sub_in_another_company_is_allowed(engine):
    def action(connection):
        person = uuid4()
        _user(connection, _company(connection), person_identity_id=person, keycloak_user_id="sub-1")
        _user(connection, _company(connection), person_identity_id=person, keycloak_user_id="sub-1")

    assert not _violates(engine, action)


@pytest.mark.parametrize("sub", ["", " sub", "sub "])
def test_keycloak_user_id_not_blank_and_trimmed(engine, sub):
    assert _violates(engine, lambda c: _user(c, _company(c), keycloak_user_id=sub))


def test_person_identity_is_required(engine):
    assert _violates(engine, lambda c: _user(c, _company(c), person_identity_id=None))


def test_membership_status_check(engine):
    assert _violates(engine, lambda c: _user(c, _company(c), status="DELETED"))


# --------------------------------------------------------------- user_branches


def _user_branch(connection, user_id, branch_id, company_id, **overrides):
    values = {
        "id": uuid4(),
        "application_user_id": user_id,
        "branch_id": branch_id,
        "company_id": company_id,
        "assigned_by": "test",
        **AUDIT,
    }
    values.update(overrides)
    _insert(connection, "user_branches", values)


def test_user_and_branch_of_the_same_company(engine):
    def ok(connection):
        company = _company(connection)
        _user_branch(connection, _user(connection, company), _branch(connection, company), company)

    assert not _violates(engine, ok)


def test_user_of_company_a_and_branch_of_company_b_is_rejected(engine):
    """RC-06: la FK compuesta impide mezclar empresas."""

    def action(connection):
        company_a = _company(connection)
        company_b = _company(connection)
        user = _user(connection, company_a)
        branch = _branch(connection, company_b)
        _user_branch(connection, user, branch, company_a)

    assert _violates(engine, action)


def test_user_branch_unique_pair_including_inactive(engine):
    """FR-021: la pareja usuario + sucursal es única en todas las filas (se reactiva)."""

    def action(connection):
        company = _company(connection)
        user = _user(connection, company)
        branch = _branch(connection, company)
        _user_branch(connection, user, branch, company)
        _user_branch(
            connection,
            user,
            branch,
            company,
            status="INACTIVE",
            deactivated_at="2026-01-01T00:00:00+00:00",
        )

    assert _violates(engine, action)


@pytest.mark.parametrize(
    ("status", "deactivated"),
    [("ACTIVE", True), ("INACTIVE", False)],
)
def test_user_branch_deactivation_consistency(engine, status, deactivated):
    def action(connection):
        company = _company(connection)
        values = {"status": status}
        if deactivated:
            values["deactivated_at"] = "2026-01-01T00:00:00+00:00"
        _user_branch(connection, _user(connection, company), _branch(connection, company), company, **values)

    assert _violates(engine, action)


def test_user_branch_assigned_by_required(engine):
    def action(connection):
        company = _company(connection)
        _user_branch(
            connection,
            _user(connection, company),
            _branch(connection, company),
            company,
            assigned_by="  ",
        )

    assert _violates(engine, action)


# --------------------------------------------------------------- advisors


def test_single_active_primary_advisor_per_company(engine):
    def action(connection):
        company = _company(connection)
        _advisor(connection, company)
        _advisor(connection, company)

    assert _violates(engine, action)


def test_non_primary_and_closed_advisors_are_allowed(engine):
    def action(connection):
        company = _company(connection)
        _advisor(connection, company)
        _advisor(connection, company, is_primary=False)
        _advisor(
            connection,
            company,
            status="INACTIVE",
            valid_from="2026-01-01T00:00:00+00:00",
            valid_to="2026-02-01T00:00:00+00:00",
        )

    assert not _violates(engine, action)


def test_same_person_twice_active_in_company_is_rejected(engine):
    def action(connection):
        company = _company(connection)
        person = uuid4()
        _advisor(connection, company, person_identity_id=person)
        _advisor(connection, company, person_identity_id=person, is_primary=False)

    assert _violates(engine, action)


@pytest.mark.parametrize(
    "values",
    [
        {"status": "ACTIVE", "valid_to": "2026-02-01T00:00:00+00:00"},
        {"status": "INACTIVE"},
        {
            "status": "INACTIVE",
            "valid_from": "2026-02-01T00:00:00+00:00",
            "valid_to": "2026-02-01T00:00:00+00:00",
        },
    ],
)
def test_advisor_validity_invariant(engine, values):
    assert _violates(engine, lambda c: _advisor(c, _company(c), **values))


# --------------------------------------------------------------- RESTRICT


def test_company_with_members_cannot_be_deleted(engine):
    def action(connection):
        company = _company(connection)
        _user(connection, company)
        connection.execute(text("DELETE FROM companies WHERE id = :id"), {"id": company})

    assert _violates(engine, action)


def test_membership_with_assignments_cannot_be_deleted(engine):
    def action(connection):
        company = _company(connection)
        user = _user(connection, company)
        _user_branch(connection, user, _branch(connection, company), company)
        connection.execute(text("DELETE FROM application_users WHERE id = :id"), {"id": user})

    assert _violates(engine, action)
