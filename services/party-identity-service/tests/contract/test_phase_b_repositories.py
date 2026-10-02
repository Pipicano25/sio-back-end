"""Repositorios de la Fase B contra la base de pruebas (T027)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from party_identity_service.application.exceptions import (
    ContactProfileAlreadyClosedError,
    ContactProfileNotFoundError,
    DuplicateActiveContactPersonError,
    DuplicateActiveRepresentativeError,
    DuplicateActiveSectorAssignmentError,
    DuplicateSectorCodeError,
    InvalidPrimaryContactError,
    InvalidPrimarySectorError,
    InvalidStatusTransitionError,
    PrimaryContactConflictError,
    PrimaryRepresentativeConflictError,
    PrimarySectorConflictError,
    VersionConflictError,
)
from party_identity_service.domain.contact import ContactData
from party_identity_service.infrastructure.business_sector_repository import (
    SectorSeedRow,
    SQLAlchemyBusinessSectorRepository,
)
from party_identity_service.infrastructure.contact_person_repository import (
    SQLAlchemyContactPersonRepository,
)
from party_identity_service.infrastructure.contact_profile_repository import (
    organization_contact_profile_repository,
    person_contact_profile_repository,
)
from party_identity_service.infrastructure.legal_representative_repository import (
    SQLAlchemyLegalRepresentativeRepository,
)
from party_identity_service.infrastructure.organization_business_sector_repository import (
    SQLAlchemyOrganizationBusinessSectorRepository,
    closing_instant,
)
from party_identity_service.infrastructure.organization_identity_repository import (
    SQLAlchemyOrganizationIdentityRepository,
)
from party_identity_service.infrastructure.person_identity_repository import (
    SQLAlchemyPersonIdentityRepository,
)
from tests.conftest import COLOMBIA_ID

ACTOR = "user-admin"


def _data(email: str = "ana@ejemplo-ficticio.co") -> ContactData:
    return ContactData.normalized(
        email=email, phone=None, address_line=None, country_id=None,
        administrative_division_id=None, city_id=None, postal_code=None,
    )


@pytest.fixture
def organization(db_session):
    return SQLAlchemyOrganizationIdentityRepository(db_session).create(
        country_id=COLOMBIA_ID, identification_type="NIT", identification_number="900000001-1",
        legal_name="ORG FICTICIA", trade_name=None, organization_type=None,
        registration_status=None, website=None, actor_id=ACTOR,
    )


@pytest.fixture
def person(db_session):
    return _new_person(db_session, "1000000001")


def _new_person(session, number: str):
    return SQLAlchemyPersonIdentityRepository(session).create(
        identification_country_id=COLOMBIA_ID, identification_type="CC", identification_number=number,
        first_name="ANA", middle_name=None, last_name="PRUEBA", second_last_name=None,
        birth_date=None, verification_status="UNVERIFIED", actor_id=ACTOR,
    )


# --- Perfiles -------------------------------------------------------------------


def test_profile_replace_closes_and_creates_in_one_transaction(db_session, organization) -> None:
    repository = organization_contact_profile_repository(db_session)
    company, user = uuid4(), uuid4()

    first = repository.replace(
        organization.id, expected_active_id=None, expected_version=None, data=_data(),
        confirmed_by_company_id=company, confirmed_by_user_id=user, actor_id=ACTOR,
    )
    second = repository.replace(
        organization.id, expected_active_id=first.id, expected_version=first.version,
        data=_data("otra@ejemplo-ficticio.co"), confirmed_by_company_id=company,
        confirmed_by_user_id=user, actor_id=ACTOR,
    )

    closed = repository.get_version(first.id)
    assert closed.is_active is False and closed.valid_to == second.valid_from
    assert repository.get_active(organization.id).id == second.id
    history = repository.list_versions(organization.id, page=1, page_size=10)
    assert [item.id for item in history.items] == [second.id, first.id]


def test_profile_replace_detects_stale_view(db_session, organization) -> None:
    repository = organization_contact_profile_repository(db_session)
    current = repository.replace(
        organization.id, expected_active_id=None, expected_version=None, data=_data(),
        confirmed_by_company_id=uuid4(), confirmed_by_user_id=uuid4(), actor_id=ACTOR,
    )

    with pytest.raises(VersionConflictError):
        repository.replace(
            organization.id, expected_active_id=None, expected_version=None, data=_data(),
            confirmed_by_company_id=uuid4(), confirmed_by_user_id=uuid4(), actor_id=ACTOR,
        )
    with pytest.raises(VersionConflictError):
        repository.replace(
            organization.id, expected_active_id=current.id, expected_version=current.version + 5,
            data=_data(), confirmed_by_company_id=uuid4(), confirmed_by_user_id=uuid4(), actor_id=ACTOR,
        )


def test_profile_close_semantics(db_session, person) -> None:
    repository = person_contact_profile_repository(db_session)

    with pytest.raises(ContactProfileNotFoundError):
        repository.close(person.id, expected_version=1, actor_id=ACTOR)

    current = repository.replace(
        person.id, expected_active_id=None, expected_version=None, data=_data(),
        confirmed_by_company_id=uuid4(), confirmed_by_user_id=uuid4(), actor_id=ACTOR,
    )
    with pytest.raises(VersionConflictError):
        repository.close(person.id, expected_version=current.version + 1, actor_id=ACTOR)

    closed = repository.close(person.id, expected_version=current.version, actor_id=ACTOR)
    assert closed.is_active is False and closed.valid_to is not None
    assert repository.get_active(person.id) is None
    assert repository.has_history(person.id) is True

    with pytest.raises(ContactProfileAlreadyClosedError):
        repository.close(person.id, expected_version=closed.version, actor_id=ACTOR)


# --- Personas de contacto ---------------------------------------------------------


def test_contact_persons_primary_and_duplicates(db_session, organization, person) -> None:
    repository = SQLAlchemyContactPersonRepository(db_session)
    primary = repository.create(
        organization_id=organization.id, person_identity_id=None, position="Compras",
        email="c@ejemplo-ficticio.co", phone=None, is_primary=True, actor_id=ACTOR,
    )
    other = repository.create(
        organization_id=organization.id, person_identity_id=person.id, position=None,
        email=None, phone=None, is_primary=False, actor_id=ACTOR,
    )

    with pytest.raises(PrimaryContactConflictError):
        repository.create(
            organization_id=organization.id, person_identity_id=None, position=None,
            email="x@ejemplo-ficticio.co", phone=None, is_primary=True, actor_id=ACTOR,
        )
    with pytest.raises(DuplicateActiveContactPersonError):
        repository.create(
            organization_id=organization.id, person_identity_id=person.id, position=None,
            email=None, phone=None, is_primary=False, actor_id=ACTOR,
        )

    switched = repository.set_primary(other.id, expected_version=other.version, actor_id=ACTOR)
    assert switched.is_primary is True
    assert repository.get_by_id(primary.id).is_primary is False

    inactive = repository.set_active(switched.id, expected_version=switched.version, active=False, actor_id=ACTOR)
    assert inactive.is_primary is False and inactive.is_active is False
    with pytest.raises(InvalidPrimaryContactError):
        repository.set_primary(inactive.id, expected_version=inactive.version, actor_id=ACTOR)


# --- Sectores ---------------------------------------------------------------------


def test_business_sectors_catalog_and_hierarchy(db_session) -> None:
    repository = SQLAlchemyBusinessSectorRepository(db_session)
    root = repository.create(parent_sector_id=None, classification_system="TEST", code="A",
                             name="Raíz", description=None, actor_id=ACTOR)
    child = repository.create(parent_sector_id=root.id, classification_system="TEST", code="01",
                              name="Hijo", description=None, actor_id=ACTOR)

    with pytest.raises(DuplicateSectorCodeError):
        repository.create(parent_sector_id=None, classification_system="TEST", code="A",
                          name="Otro", description=None, actor_id=ACTOR)

    assert repository.has_active_children(root.id) is True
    assert set(repository.ancestor_ids(child.id)) == {child.id, root.id}
    page = repository.list_all(page=1, page_size=10, classification_system="TEST", roots_only=True)
    assert [sector.code for sector in page.items] == ["A"]


def test_business_sector_upsert_is_idempotent_and_single_transaction(db_session) -> None:
    repository = SQLAlchemyBusinessSectorRepository(db_session)
    rows = [SectorSeedRow("A", "Sección A", None), SectorSeedRow("01", "División 01", "A")]

    first = repository.upsert_catalog(classification_system="TEST", rows=rows, actor_id="system:test")
    ids = {sector.code: sector.id for sector in repository.list_all(page=1, page_size=10, classification_system="TEST").items}
    second = repository.upsert_catalog(classification_system="TEST", rows=rows, actor_id="system:test")

    assert (first.created, second.created, second.unchanged) == (2, 0, 2)
    assert {sector.code: sector.id for sector in repository.list_all(page=1, page_size=10, classification_system="TEST").items} == ids

    with pytest.raises(KeyError):
        repository.upsert_catalog(
            classification_system="OTHER",
            rows=[SectorSeedRow("B", "Sección B", None), SectorSeedRow("02", "Huérfana", "Z")],
            actor_id="system:test",
        )
    assert repository.list_all(page=1, page_size=10, classification_system="OTHER").total_records == 0


def test_organization_sectors_primary_close_and_state(db_session, organization) -> None:
    sectors = SQLAlchemyBusinessSectorRepository(db_session)
    first = sectors.create(parent_sector_id=None, classification_system="TEST", code="01", name="Uno",
                           description=None, actor_id=ACTOR)
    second = sectors.create(parent_sector_id=None, classification_system="TEST", code="02", name="Dos",
                            description=None, actor_id=ACTOR)
    repository = SQLAlchemyOrganizationBusinessSectorRepository(db_session)

    primary = repository.create(organization_id=organization.id, sector_id=first.id, is_primary=True,
                                valid_from=None, actor_id=ACTOR)
    other = repository.create(organization_id=organization.id, sector_id=second.id, is_primary=False,
                              valid_from=None, actor_id=ACTOR)
    with pytest.raises(PrimarySectorConflictError):
        repository.create(organization_id=organization.id, sector_id=second.id, is_primary=True,
                          valid_from=None, actor_id=ACTOR)
    with pytest.raises(DuplicateActiveSectorAssignmentError):
        repository.create(organization_id=organization.id, sector_id=first.id, is_primary=False,
                          valid_from=None, actor_id=ACTOR)

    switched = repository.set_primary(other.id, expected_version=other.version, actor_id=ACTOR)
    assert switched.is_primary and not repository.get_by_id(primary.id).is_primary

    closed = repository.close(switched.id, expected_version=switched.version, actor_id=ACTOR)
    assert closed.is_active is False and closed.is_primary is False and closed.valid_to is not None
    with pytest.raises(InvalidStatusTransitionError):
        repository.close(closed.id, expected_version=closed.version, actor_id=ACTOR)
    with pytest.raises(InvalidPrimarySectorError):
        repository.set_primary(closed.id, expected_version=closed.version, actor_id=ACTOR)

    assert repository.list_by_organization(organization.id, state="active", page=1, page_size=10).total_records == 1
    assert repository.list_by_organization(organization.id, state="closed", page=1, page_size=10).total_records == 1
    assert repository.list_by_organization(organization.id, state="all", page=1, page_size=10).total_records == 2


def test_closing_before_start_sets_valid_to_equal_valid_from() -> None:
    now = datetime(2026, 10, 1, tzinfo=timezone.utc)
    future = now + timedelta(days=10)

    assert closing_instant(future, now) == future
    assert closing_instant(now - timedelta(days=1), now) == now


def test_future_assignment_closed_before_start_never_was_active(db_session, organization) -> None:
    sector = SQLAlchemyBusinessSectorRepository(db_session).create(
        parent_sector_id=None, classification_system="TEST", code="09", name="Nueve",
        description=None, actor_id=ACTOR,
    )
    repository = SQLAlchemyOrganizationBusinessSectorRepository(db_session)
    future = datetime.now(timezone.utc) + timedelta(days=30)
    assignment = repository.create(organization_id=organization.id, sector_id=sector.id, is_primary=False,
                                   valid_from=future, actor_id=ACTOR)

    closed = repository.close(assignment.id, expected_version=assignment.version, actor_id=ACTOR)

    assert closed.valid_to == closed.valid_from


# --- Representantes ---------------------------------------------------------------


def test_legal_representatives_primary_set_primary_and_close(db_session, organization, person) -> None:
    second_person = _new_person(db_session, "1000000002")
    repository = SQLAlchemyLegalRepresentativeRepository(db_session)

    established, created = repository.set_primary(
        organization.id, person_identity_id=person.id, position="Gerente", valid_from=None,
        source_document_reference=None, current_primary_version=None, actor_id=ACTOR,
    )
    assert created and established.is_primary and established.representative_type == "PRIMARY"

    with pytest.raises(PrimaryRepresentativeConflictError):
        repository.create(organization_id=organization.id, person_identity_id=second_person.id,
                          representative_type="PRIMARY", position=None, valid_from=None,
                          source_document_reference=None, actor_id=ACTOR)
    with pytest.raises(DuplicateActiveRepresentativeError):
        repository.create(organization_id=organization.id, person_identity_id=person.id,
                          representative_type="ALTERNATE", position=None, valid_from=None,
                          source_document_reference=None, actor_id=ACTOR)
    with pytest.raises(VersionConflictError):
        repository.set_primary(organization.id, person_identity_id=second_person.id, position=None,
                               valid_from=None, source_document_reference=None,
                               current_primary_version=None, actor_id=ACTOR)

    same, created_again = repository.set_primary(
        organization.id, person_identity_id=person.id, position=None, valid_from=None,
        source_document_reference=None, current_primary_version=established.version, actor_id=ACTOR,
    )
    assert not created_again and same.id == established.id

    replaced, created = repository.set_primary(
        organization.id, person_identity_id=second_person.id, position=None, valid_from=None,
        source_document_reference="Acta 1 (ficticia)", current_primary_version=established.version,
        actor_id=ACTOR,
    )
    assert created and repository.get_by_id(established.id).is_active is False
    assert repository.get_active_primary(organization.id).id == replaced.id

    closed = repository.close(replaced.id, expected_version=replaced.version, actor_id=ACTOR)
    assert closed.is_active is False
    with pytest.raises(InvalidStatusTransitionError):
        repository.update(closed.id, expected_version=closed.version, values={"position": "X"}, actor_id=ACTOR)
    assert repository.list_by_organization(organization.id, state="closed", page=1, page_size=10).total_records == 2


def test_tables_are_truncated_between_tests(test_engine, db_session) -> None:
    with test_engine.connect() as connection:
        count = connection.execute(text("SELECT count(*) FROM global_business_sectors")).scalar_one()
    assert count == 0
