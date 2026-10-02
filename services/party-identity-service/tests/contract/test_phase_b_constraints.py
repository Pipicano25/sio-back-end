"""Restricciones de la base de datos de la Fase B (T013; RC-03, RC-04, FR-092, FR-093).

Cada índice único parcial rechaza el segundo registro vigente y acepta uno
cerrado/inactivo; cada `CHECK` se ejerce; las FK internas existen y no hacen
cascada; las referencias externas (`UUID REF`) no tienen FK.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import IntegrityError

AUDIT = "'user-a', 'user-a'"


def _person(connection: Connection) -> UUID:
    person_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO person_identities (id, identification_country_id, identification_type, "
            "identification_number, first_name, last_name, verification_status, status, version, "
            f"created_by, updated_by) VALUES (:id, gen_random_uuid(), 'CC', :number, 'ANA', "
            f"'PRUEBA', 'UNVERIFIED', 'ACTIVE', 1, {AUDIT})"
        ),
        {"id": person_id, "number": str(person_id.int)[:10]},
    )
    return person_id


def _organization(connection: Connection) -> UUID:
    organization_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO organization_identities (id, country_id, identification_type, "
            "identification_number, legal_name, status, version, created_by, updated_by) "
            f"VALUES (:id, gen_random_uuid(), 'NIT', :number, 'ORG FICTICIA', 'ACTIVE', 1, {AUDIT})"
        ),
        {"id": organization_id, "number": str(organization_id.int)[:10]},
    )
    return organization_id


def _sector(connection: Connection, code: str, parent: UUID | None = None, system: str = "TEST") -> UUID:
    sector_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO global_business_sectors (id, parent_sector_id, classification_system, code, "
            f"name, status, version, created_by, updated_by) VALUES (:id, :parent, :system, :code, "
            f"'Sector', 'ACTIVE', 1, {AUDIT})"
        ),
        {"id": sector_id, "parent": parent, "system": system, "code": code},
    )
    return sector_id


def _profile(connection: Connection, table: str, owner_column: str, owner: UUID, **overrides) -> UUID:
    values = {
        "id": uuid4(),
        "owner": owner,
        "email": "ana@ejemplo-ficticio.co",
        "phone": None,
        "address_line": None,
        "country_id": None,
        "administrative_division_id": None,
        "city_id": None,
        "is_active": True,
        "valid_to": None,
        "confirmed_by_user_id": uuid4(),
        "confirmed_by_company_id": uuid4(),
    }
    values.update(overrides)
    connection.execute(
        text(
            f"INSERT INTO {table} (id, {owner_column}, email, phone, address_line, country_id, "
            "administrative_division_id, city_id, is_active, valid_from, valid_to, "
            "confirmed_by_user_id, confirmed_by_company_id, version, created_by, updated_by) "
            "VALUES (:id, :owner, :email, :phone, :address_line, :country_id, "
            ":administrative_division_id, :city_id, :is_active, now() - interval '1 day', :valid_to, "
            f":confirmed_by_user_id, :confirmed_by_company_id, 1, {AUDIT})"
        ),
        values,
    )
    return values["id"]


def _contact_person(connection: Connection, organization: UUID, **overrides) -> UUID:
    values = {"id": uuid4(), "org": organization, "person": None, "email": "c@ejemplo-ficticio.co",
              "phone": None, "is_primary": False, "is_active": True}
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO organization_contact_persons (id, organization_identity_id, person_identity_id, "
            "email, phone, is_primary, is_active, version, created_by, updated_by) VALUES (:id, :org, "
            f":person, :email, :phone, :is_primary, :is_active, 1, {AUDIT})"
        ),
        values,
    )
    return values["id"]


def _org_sector(connection: Connection, organization: UUID, sector: UUID, **overrides) -> UUID:
    values = {"id": uuid4(), "org": organization, "sector": sector, "is_primary": False,
              "is_active": True, "valid_to": None}
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO organization_business_sectors (id, organization_identity_id, "
            "global_business_sector_id, is_primary, is_active, valid_from, valid_to, version, "
            f"created_by, updated_by) VALUES (:id, :org, :sector, :is_primary, :is_active, "
            f"now() - interval '1 day', :valid_to, 1, {AUDIT})"
        ),
        values,
    )
    return values["id"]


def _representative(connection: Connection, organization: UUID, person: UUID, **overrides) -> UUID:
    values = {"id": uuid4(), "org": organization, "person": person, "type": "PRIMARY",
              "is_primary": True, "is_active": True, "valid_to": None, "doc": None}
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO organization_legal_representatives (id, organization_identity_id, "
            "person_identity_id, representative_type, is_primary, is_active, valid_from, valid_to, "
            "source_document_reference, version, created_by, updated_by) VALUES (:id, :org, :person, "
            ":type, :is_primary, :is_active, now() - interval '1 day', :valid_to, :doc, 1, "
            f"{AUDIT})"
        ),
        values,
    )
    return values["id"]


def _expect_violation(engine: Engine, constraint: str, action: Callable[[Connection], None]) -> None:
    with pytest.raises(IntegrityError) as error:
        with engine.begin() as connection:
            action(connection)
    assert constraint in str(error.value.orig)


@pytest.fixture
def engine(test_engine: Engine, clean_database: None) -> Engine:
    return test_engine


# --- Índices únicos parciales -------------------------------------------------


@pytest.mark.parametrize(
    "table, owner_column, owner_factory",
    [
        ("person_contact_profiles", "person_identity_id", _person),
        ("organization_contact_profiles", "organization_identity_id", _organization),
    ],
)
def test_one_active_profile_per_owner(engine: Engine, table: str, owner_column: str, owner_factory) -> None:
    with engine.begin() as connection:
        owner = owner_factory(connection)
        _profile(connection, table, owner_column, owner)
        connection.execute(
            text(f"UPDATE {table} SET is_active = false, valid_to = now()")
        )
        # Una versión cerrada no cuenta para la unicidad: se admite una nueva vigente.
        _profile(connection, table, owner_column, owner)

    _expect_violation(
        engine,
        f"uq_{table}_active",
        lambda connection: _profile(connection, table, owner_column, owner),
    )


def test_one_primary_contact_and_one_active_person_per_organization(engine: Engine) -> None:
    with engine.begin() as connection:
        organization = _organization(connection)
        person = _person(connection)
        _contact_person(connection, organization, is_primary=True)
        _contact_person(connection, organization, person=person)
        _contact_person(connection, organization, is_active=False, is_primary=False, person=person)

    _expect_violation(
        engine,
        "uq_organization_contact_persons_primary",
        lambda connection: _contact_person(connection, organization, is_primary=True),
    )
    _expect_violation(
        engine,
        "uq_organization_contact_persons_person",
        lambda connection: _contact_person(connection, organization, person=person),
    )


def test_sector_code_unique_per_system(engine: Engine) -> None:
    with engine.begin() as connection:
        _sector(connection, "A")
        _sector(connection, "A", system="OTHER")

    _expect_violation(
        engine,
        "uq_global_business_sectors_system_code",
        lambda connection: _sector(connection, "A"),
    )


def test_closed_assignment_requires_valid_to(engine: Engine) -> None:
    with engine.begin() as connection:
        organization = _organization(connection)
        sector = _sector(connection, "01")

    _expect_violation(
        engine,
        "ck_organization_business_sectors_validity",
        lambda connection: _org_sector(connection, organization, sector, is_active=False, valid_to=None),
    )


def test_assignment_partial_indexes(engine: Engine) -> None:
    with engine.begin() as connection:
        organization = _organization(connection)
        first = _sector(connection, "01")
        second = _sector(connection, "02")
        _org_sector(connection, organization, first, is_primary=True)
        connection.execute(text(
            "INSERT INTO organization_business_sectors (id, organization_identity_id, "
            "global_business_sector_id, is_primary, is_active, valid_from, valid_to, version, "
            f"created_by, updated_by) VALUES (gen_random_uuid(), :org, :sector, false, false, "
            f"now() - interval '2 day', now() - interval '1 day', 1, {AUDIT})"
        ), {"org": organization, "sector": first})

    _expect_violation(
        engine,
        "uq_organization_business_sectors_active",
        lambda connection: _org_sector(connection, organization, first),
    )
    _expect_violation(
        engine,
        "uq_organization_business_sectors_primary",
        lambda connection: _org_sector(connection, organization, second, is_primary=True),
    )


def test_one_primary_representative_and_one_active_relation_per_person(engine: Engine) -> None:
    with engine.begin() as connection:
        organization = _organization(connection)
        first = _person(connection)
        second = _person(connection)
        _representative(connection, organization, first)

    _expect_violation(
        engine,
        "uq_organization_legal_representatives_primary",
        lambda connection: _representative(connection, organization, second),
    )
    _expect_violation(
        engine,
        "uq_organization_legal_representatives_person",
        lambda connection: _representative(
            connection, organization, first, type="ALTERNATE", is_primary=False
        ),
    )


# --- CHECK --------------------------------------------------------------------


@pytest.mark.parametrize(
    "table, owner_column, owner_factory",
    [
        ("person_contact_profiles", "person_identity_id", _person),
        ("organization_contact_profiles", "organization_identity_id", _organization),
    ],
)
def test_profile_checks(engine: Engine, table: str, owner_column: str, owner_factory) -> None:
    with engine.begin() as connection:
        owner = owner_factory(connection)

    _expect_violation(engine, f"ck_{table}_has_contact", lambda c: _profile(
        c, table, owner_column, owner, email=None))
    _expect_violation(engine, f"ck_{table}_validity", lambda c: _profile(
        c, table, owner_column, owner, is_active=False, valid_to=None))
    _expect_violation(engine, f"ck_{table}_geography_parent", lambda c: _profile(
        c, table, owner_column, owner, city_id=uuid4()))
    _expect_violation(engine, f"ck_{table}_geography_parent", lambda c: _profile(
        c, table, owner_column, owner, administrative_division_id=uuid4()))


def test_validity_range_allows_equal_and_rejects_earlier(engine: Engine) -> None:
    """Vigencia `[valid_from, valid_to)`: `valid_to = valid_from` = nunca vigente (R-05a)."""
    with engine.begin() as connection:
        organization = _organization(connection)
        sector = _sector(connection, "01")
        connection.execute(text(
            "INSERT INTO organization_business_sectors (id, organization_identity_id, "
            "global_business_sector_id, is_primary, is_active, valid_from, valid_to, version, "
            "created_by, updated_by) VALUES (gen_random_uuid(), :org, :sector, false, false, "
            f"'2030-01-01', '2030-01-01', 1, {AUDIT})"
        ), {"org": organization, "sector": sector})

    _expect_violation(engine, "ck_organization_business_sectors_validity_range", lambda c: c.execute(text(
        "INSERT INTO organization_business_sectors (id, organization_identity_id, "
        "global_business_sector_id, is_primary, is_active, valid_from, valid_to, version, "
        "created_by, updated_by) VALUES (gen_random_uuid(), :org, :sector, false, false, "
        f"'2030-01-02', '2030-01-01', 1, {AUDIT})"
    ), {"org": organization, "sector": sector}))


def test_contact_person_checks(engine: Engine) -> None:
    with engine.begin() as connection:
        organization = _organization(connection)

    _expect_violation(engine, "ck_organization_contact_persons_has_contact", lambda c: _contact_person(
        c, organization, email=None))
    _expect_violation(engine, "ck_organization_contact_persons_primary_active", lambda c: _contact_person(
        c, organization, is_primary=True, is_active=False))


def test_assignment_primary_requires_active(engine: Engine) -> None:
    with engine.begin() as connection:
        organization = _organization(connection)
        sector = _sector(connection, "01")

    _expect_violation(engine, "ck_organization_business_sectors_primary_active", lambda c: c.execute(text(
        "INSERT INTO organization_business_sectors (id, organization_identity_id, "
        "global_business_sector_id, is_primary, is_active, valid_from, valid_to, version, "
        "created_by, updated_by) VALUES (gen_random_uuid(), :org, :sector, true, false, "
        f"now() - interval '2 day', now(), 1, {AUDIT})"
    ), {"org": organization, "sector": sector}))


def test_representative_checks(engine: Engine) -> None:
    with engine.begin() as connection:
        organization = _organization(connection)
        person = _person(connection)

    _expect_violation(engine, "ck_organization_legal_representatives_type", lambda c: _representative(
        c, organization, person, type="BOSS", is_primary=False))
    _expect_violation(engine, "ck_organization_legal_representatives_primary_flag", lambda c: _representative(
        c, organization, person, type="ALTERNATE", is_primary=True))
    _expect_violation(engine, "ck_organization_legal_representatives_doc_not_blank", lambda c: _representative(
        c, organization, person, doc="   "))


def test_sector_checks(engine: Engine) -> None:
    sector_id = uuid4()
    _expect_violation(engine, "ck_global_business_sectors_status", lambda c: c.execute(text(
        "INSERT INTO global_business_sectors (id, classification_system, code, name, status, version, "
        f"created_by, updated_by) VALUES (gen_random_uuid(), 'T', 'X', 'n', 'BAD', 1, {AUDIT})"
    )))
    _expect_violation(engine, "ck_global_business_sectors_not_self_parent", lambda c: c.execute(text(
        "INSERT INTO global_business_sectors (id, parent_sector_id, classification_system, code, name, "
        f"status, version, created_by, updated_by) VALUES (:id, :id, 'T', 'Y', 'n', 'ACTIVE', 1, {AUDIT})"
    ), {"id": sector_id}))


# --- FK internas y referencias externas -----------------------------------------


def test_internal_foreign_keys_reject_unknown_owner(engine: Engine) -> None:
    _expect_violation(engine, "fk_person_contact_profiles_person_identity_id", lambda c: _profile(
        c, "person_contact_profiles", "person_identity_id", uuid4()))
    _expect_violation(engine, "fk_organization_contact_persons_organization_identity_id",
                      lambda c: _contact_person(c, uuid4()))


def test_foreign_keys_do_not_cascade(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = (
        "person_contact_profiles",
        "organization_contact_profiles",
        "organization_contact_persons",
        "global_business_sectors",
        "organization_business_sectors",
        "organization_legal_representatives",
    )
    for table in tables:
        for foreign_key in inspector.get_foreign_keys(table):
            assert foreign_key["options"].get("ondelete") in (None, "RESTRICT", "NO ACTION"), table
            assert foreign_key["referred_table"] in {
                "person_identities", "organization_identities", "global_business_sectors"
            }, table


def test_external_references_have_no_foreign_key_and_are_required(engine: Engine) -> None:
    inspector = inspect(engine)
    for table in ("person_contact_profiles", "organization_contact_profiles"):
        constrained = {
            column
            for foreign_key in inspector.get_foreign_keys(table)
            for column in foreign_key["constrained_columns"]
        }
        assert not constrained & {
            "country_id", "administrative_division_id", "city_id",
            "confirmed_by_company_id", "confirmed_by_user_id",
        }
        columns = {column["name"]: column for column in inspector.get_columns(table)}
        assert columns["confirmed_by_user_id"]["nullable"] is False
        assert columns["confirmed_by_company_id"]["nullable"] is False

    with engine.begin() as connection:
        organization = _organization(connection)
        _profile(connection, "organization_contact_profiles", "organization_identity_id", organization,
                 country_id=uuid4(), administrative_division_id=uuid4(), city_id=uuid4())
