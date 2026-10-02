"""Servicio de perfiles: orden, atomicidad y enmascaramiento (T042; R-03, RC-02, RC-13)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from party_identity_service.application.contact_profile_service import ContactProfileService
from party_identity_service.application.exceptions import (
    DependencyUnavailableError,
    VersionConflictError,
)
from party_identity_service.domain.contact import ContactProfile

COMPANY = uuid4()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Owner:
    id: UUID
    status: str = "ACTIVE"


class Owners:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def get_by_id(self, owner_id):
        return self.owner if owner_id == self.owner.id else None


@dataclass
class Repo:
    """Repositorio en memoria que registra el orden de las llamadas."""

    events: list[str]
    active: ContactProfile | None = None
    fail_on_replace: Exception | None = None
    writes: int = 0
    concurrent_change: bool = False

    def get_active(self, owner_id):
        return self.active

    def has_history(self, owner_id):
        return self.active is not None

    def replace(self, owner_id, *, expected_active_id, expected_version, data,
                confirmed_by_company_id, confirmed_by_user_id, actor_id):
        self.events.append("lock+replace")
        if self.concurrent_change:
            raise VersionConflictError
        if self.fail_on_replace is not None:
            raise self.fail_on_replace
        self.writes += 1
        now = _now()
        self.active = ContactProfile(
            id=uuid4(), owner_id=owner_id, is_active=True, valid_from=now, valid_to=None,
            confirmed_by_user_id=confirmed_by_user_id, confirmed_by_company_id=confirmed_by_company_id,
            version=1, created_by=actor_id, updated_by=actor_id, created_at=now, updated_at=now,
            email=data.email, phone=data.phone, address_line=data.address_line,
            country_id=data.country_id, administrative_division_id=data.administrative_division_id,
            city_id=data.city_id, postal_code=data.postal_code,
        )
        return self.active


class Locations:
    def __init__(self, events: list[str], fail: bool = False) -> None:
        self.events = events
        self.fail = fail

    def get_country(self, country_id):
        from party_identity_service.application.ports import LocationRecord

        self.events.append("geography")
        if self.fail:
            raise DependencyUnavailableError(dependency="geography", cause="X")
        return LocationRecord(id=country_id, status="ACTIVE")

    def get_administrative_division(self, division_id):
        raise AssertionError("no usado")

    def get_city(self, city_id):
        raise AssertionError("no usado")


class Membership:
    def __init__(self, events: list[str], fail: bool = False) -> None:
        self.events = events
        self.fail = fail

    def resolve(self, *, company_id, keycloak_user_id):
        self.events.append("membership")
        if self.fail:
            raise DependencyUnavailableError(dependency="operational-context", cause="X")
        return uuid4()


def _service(events, repo, *, locations_fail=False, membership_fail=False, owner=None):
    owner = owner or Owner(uuid4())
    service = ContactProfileService(
        kind="organization",
        profiles=repo,
        owners=Owners(owner),
        locations=Locations(events, locations_fail),
        memberships=Membership(events, membership_fail),
    )
    return service, owner


def _register(service, owner, **overrides):
    values = dict(
        email="ana@ejemplo-ficticio.co", phone="+57 300 000 0000", address_line="Calle secreta 123",
        country_id=uuid4(), administrative_division_id=None, city_id=None, postal_code=None,
        confirmed_by_company_id=COMPANY, expected_version=None, actor_id="user-a",
        keycloak_user_id="sub-a",
    )
    values.update(overrides)
    return service.register(owner.id, **values)


def test_external_validations_happen_before_the_locked_write() -> None:
    events: list[str] = []
    repo = Repo(events)
    service, owner = _service(events, repo)

    _register(service, owner)

    assert events == ["geography", "membership", "lock+replace"]


@pytest.mark.parametrize("which", ["locations", "membership"])
def test_nothing_is_written_when_a_dependency_fails(which) -> None:
    events: list[str] = []
    repo = Repo(events)
    service, owner = _service(
        events, repo, locations_fail=which == "locations", membership_fail=which == "membership"
    )

    with pytest.raises(DependencyUnavailableError):
        _register(service, owner)

    assert repo.writes == 0 and "lock+replace" not in events


def test_concurrent_change_during_external_calls_is_conflict() -> None:
    events: list[str] = []
    repo = Repo(events, concurrent_change=True)
    service, owner = _service(events, repo)

    with pytest.raises(VersionConflictError):
        _register(service, owner)


def test_logs_do_not_contain_contact_data(caplog) -> None:
    caplog.set_level(logging.DEBUG)
    events: list[str] = []
    service, owner = _service(events, Repo(events))

    _register(service, owner)

    for secret in ("ana@ejemplo-ficticio.co", "300 000 0000", "Calle secreta 123"):
        assert secret not in caplog.text


def test_replace_failure_after_validations_propagates_without_partial_state() -> None:
    events: list[str] = []
    repo = Repo(events, fail_on_replace=RuntimeError("fallo al crear"))
    service, owner = _service(events, repo)

    with pytest.raises(RuntimeError):
        _register(service, owner)

    assert repo.active is None and repo.writes == 0


def test_atomic_replace_rolls_back_close_when_create_fails(db_session) -> None:
    """RC-02 contra la base: si la creación falla tras cerrar, el cierre se revierte."""
    from sqlalchemy import event

    from party_identity_service.domain.contact import ContactData
    from party_identity_service.infrastructure.contact_profile_repository import (
        organization_contact_profile_repository,
    )
    from party_identity_service.infrastructure.models import OrganizationContactProfileModel
    from party_identity_service.infrastructure.organization_identity_repository import (
        SQLAlchemyOrganizationIdentityRepository,
    )
    from tests.conftest import COLOMBIA_ID

    organization = SQLAlchemyOrganizationIdentityRepository(db_session).create(
        country_id=COLOMBIA_ID, identification_type="NIT", identification_number="900000005-1",
        legal_name="ORG", trade_name=None, organization_type=None, registration_status=None,
        website=None, actor_id="user-a",
    )
    repository = organization_contact_profile_repository(db_session)
    data = ContactData.normalized(email="a@ejemplo-ficticio.co", phone=None, address_line=None,
                                  country_id=None, administrative_division_id=None, city_id=None,
                                  postal_code=None)
    first = repository.replace(organization.id, expected_active_id=None, expected_version=None, data=data,
                               confirmed_by_company_id=COMPANY, confirmed_by_user_id=uuid4(), actor_id="u")

    def fail_insert(mapper, connection, target):
        raise RuntimeError("fallo simulado al insertar la versión nueva")

    event.listen(OrganizationContactProfileModel, "before_insert", fail_insert)
    try:
        with pytest.raises(RuntimeError):
            repository.replace(organization.id, expected_active_id=first.id, expected_version=first.version,
                               data=data, confirmed_by_company_id=COMPANY, confirmed_by_user_id=uuid4(),
                               actor_id="u")
    finally:
        event.remove(OrganizationContactProfileModel, "before_insert", fail_insert)
        db_session.rollback()

    current = repository.get_active(organization.id)
    assert current is not None and current.id == first.id and current.is_active
