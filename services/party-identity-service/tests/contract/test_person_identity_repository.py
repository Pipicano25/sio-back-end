"""Pruebas del repositorio de personas sobre PostgreSQL (RC-02, FR-020, FR-024, DS-10)."""

from datetime import date
from uuid import uuid4

import pytest

from party_identity_service.application.exceptions import (
    DuplicateIdentificationError,
)
from party_identity_service.infrastructure.person_identity_repository import (
    SQLAlchemyPersonIdentityRepository,
)
from tests.conftest import COLOMBIA_ID


@pytest.fixture
def repository(db_session) -> SQLAlchemyPersonIdentityRepository:
    return SQLAlchemyPersonIdentityRepository(db_session)


def _create(repository, number="1000000001", **overrides):
    values = {
        "identification_country_id": COLOMBIA_ID,
        "identification_type": "CC",
        "identification_number": number,
        "first_name": "ANA",
        "middle_name": None,
        "last_name": "PRUEBA",
        "second_last_name": None,
        "birth_date": date(1990, 5, 10),
        "verification_status": "UNVERIFIED",
        "actor_id": "user-admin",
    }
    values.update(overrides)
    return repository.create(**values)


def _list(repository, **filters):
    return repository.list_all(page=1, page_size=20, **filters)


def test_create_defaults_to_active_with_text_actor(repository) -> None:
    person = _create(repository)

    assert person.status == "ACTIVE"
    assert person.version == 1
    assert person.created_by == "user-admin"
    assert person.updated_by == "user-admin"


def test_duplicate_identification_is_translated(repository) -> None:
    _create(repository)

    with pytest.raises(DuplicateIdentificationError):
        _create(repository, first_name="OTRA")


def test_uniqueness_includes_inactive_identities(repository) -> None:
    person = _create(repository)
    repository.set_status(person.id, expected_version=1, status="INACTIVE", actor_id="user-admin")

    with pytest.raises(DuplicateIdentificationError):
        _create(repository)


def test_list_defaults_to_active_and_filters_inactive_explicitly(repository) -> None:
    active = _create(repository, "1000000001")
    inactive = _create(repository, "1000000002")
    repository.set_status(inactive.id, expected_version=1, status="INACTIVE", actor_id="user-admin")

    assert [item.id for item in _list(repository).items] == [active.id]
    assert [item.id for item in _list(repository, status="INACTIVE").items] == [inactive.id]


def test_filters_by_country_type_and_verification(repository) -> None:
    other_country = uuid4()
    target = _create(repository, "1000000001", verification_status="VERIFIED")
    _create(repository, "1000000002", identification_country_id=other_country)
    _create(repository, "1000000003", identification_type="TI")

    assert [p.id for p in _list(repository, identification_country_id=COLOMBIA_ID, identification_type="CC").items] == [target.id]
    assert [p.id for p in _list(repository, verification_status="VERIFIED").items] == [target.id]


@pytest.mark.parametrize("term", ["00000001", "ana", "PRUEB"])
def test_search_by_number_and_names(repository, term) -> None:
    person = _create(repository, "1000000001")
    _create(repository, "2000000002", first_name="LUIS", last_name="OTRO")

    assert [p.id for p in _list(repository, search=term).items] == [person.id]


def test_pagination(repository) -> None:
    for index in range(5):
        _create(repository, f"100000000{index}", last_name=f"APELLIDO{index}")

    page = repository.list_all(page=2, page_size=2)

    assert page.total_records == 5
    assert page.total_pages == 3
    assert len(page.items) == 2
