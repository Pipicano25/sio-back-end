"""Pruebas del repositorio de organizaciones sobre PostgreSQL (RC-02, FR-030, FR-032, DS-10).

Conserva las comprobaciones previas (alta sin dígito de verificación separado,
duplicado, actualización con versión y versión desactualizada) sobre el nuevo
contrato del repositorio.
"""

from uuid import uuid4

import pytest

from party_identity_service.application.exceptions import (
    DuplicateIdentificationError,
    NotFoundError,
    VersionConflictError,
)
from party_identity_service.infrastructure.models import (
    OrganizationIdentityModel,
)
from party_identity_service.infrastructure.organization_identity_repository import (
    SQLAlchemyOrganizationIdentityRepository,
)
from tests.conftest import COLOMBIA_ID

ACTOR_ID = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def repository(db_session) -> SQLAlchemyOrganizationIdentityRepository:
    return SQLAlchemyOrganizationIdentityRepository(db_session)


def _create(repository, number="900000001-1", **overrides):
    values = {
        "country_id": COLOMBIA_ID,
        "identification_type": "NIT",
        "identification_number": number,
        "legal_name": "ORGANIZACION FICTICIA S.A.S.",
        "trade_name": None,
        "organization_type": None,
        "registration_status": None,
        "website": None,
        "actor_id": ACTOR_ID,
    }
    values.update(overrides)
    return repository.create(**values)


def _list(repository, **filters):
    return repository.list_all(page=1, page_size=20, **filters)


def test_create_persists_organization_without_verification_digit(repository, db_session) -> None:
    organization = _create(repository)
    stored = db_session.get(OrganizationIdentityModel, organization.id)

    assert stored.identification_number == "900000001-1"
    assert not hasattr(stored, "verification_digit")
    assert stored.status == "ACTIVE"
    assert stored.created_by == ACTOR_ID


def test_create_rejects_duplicate_organization_identification(repository) -> None:
    _create(repository)

    with pytest.raises(DuplicateIdentificationError):
        _create(repository, legal_name="OTRA")


def test_uniqueness_includes_inactive_organizations(repository) -> None:
    organization = _create(repository)
    repository.set_status(organization.id, expected_version=1, status="INACTIVE", actor_id=ACTOR_ID)

    with pytest.raises(DuplicateIdentificationError):
        _create(repository)


def test_update_changes_organization_and_increments_version(repository) -> None:
    organization = _create(repository)

    updated = repository.update(
        organization.id,
        expected_version=1,
        values={"legal_name": "NUEVA RAZON SOCIAL"},
        actor_id="otro-usuario",
    )

    assert updated.legal_name == "NUEVA RAZON SOCIAL"
    assert updated.version == 2
    assert updated.updated_by == "otro-usuario"
    assert updated.created_by == ACTOR_ID


def test_update_rejects_stale_version(repository) -> None:
    organization = _create(repository)
    repository.update(organization.id, expected_version=1, values={"legal_name": "A"}, actor_id=ACTOR_ID)

    with pytest.raises(VersionConflictError):
        repository.update(organization.id, expected_version=1, values={"legal_name": "B"}, actor_id=ACTOR_ID)


def test_update_of_missing_organization_is_not_found(repository) -> None:
    with pytest.raises(NotFoundError):
        repository.update(uuid4(), expected_version=1, values={"legal_name": "X"}, actor_id=ACTOR_ID)


def test_list_defaults_to_active_and_filters(repository) -> None:
    active = _create(repository, "900000001-1", registration_status="ACTIVA")
    inactive = _create(repository, "900000002-2")
    other_country = _create(repository, "900000003-3", country_id=uuid4())
    repository.set_status(inactive.id, expected_version=1, status="INACTIVE", actor_id=ACTOR_ID)

    assert {o.id for o in _list(repository).items} == {active.id, other_country.id}
    assert [o.id for o in _list(repository, status="INACTIVE").items] == [inactive.id]
    assert [o.id for o in _list(repository, country_id=COLOMBIA_ID).items] == [active.id]
    assert [o.id for o in _list(repository, registration_status="ACTIVA").items] == [active.id]
    assert [o.id for o in _list(repository, identification_type="NIT", country_id=COLOMBIA_ID).items] == [active.id]


@pytest.mark.parametrize("term", ["00001-1", "ficticia", "COMERCIAL"])
def test_search_by_number_legal_and_trade_name(repository, term) -> None:
    organization = _create(repository, "900000001-1", trade_name="NOMBRE COMERCIAL")
    _create(repository, "800000002-2", legal_name="OTRA EMPRESA")

    assert [o.id for o in _list(repository, search=term).items] == [organization.id]
