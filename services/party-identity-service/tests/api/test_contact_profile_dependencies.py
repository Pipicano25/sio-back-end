"""Geografía y confirmación en perfiles (T040; FR-027–FR-030, FR-036, RC-15, SC-011)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from party_identity_service.application.ports import LocationRecord
from tests.conftest import CITY_ID, COLOMBIA_ID, COMPANY_ID, DIVISION_ID
from tests.phase_b import code, create_organization, profile_payload, profile_url


@pytest.fixture
def url(api):
    return profile_url("organization", create_organization(api)["id"])


def _assert_nothing_written(api, url) -> None:
    assert api.get(f"{url}/versions").json()["total_records"] == 0


@pytest.mark.parametrize(
    "overrides, expected",
    [
        ({"country_id": None}, "GEOGRAPHY_PARENT_REQUIRED"),
        ({"country_id": str(uuid4()), "administrative_division_id": None, "city_id": None}, "COUNTRY_NOT_FOUND"),
        ({"administrative_division_id": str(uuid4()), "city_id": None}, "ADMINISTRATIVE_DIVISION_NOT_FOUND"),
        ({"city_id": str(uuid4())}, "CITY_NOT_FOUND"),
    ],
)
def test_geography_errors_are_rejected_without_writing(api, url, overrides, expected) -> None:
    response = api.post(url, json=profile_payload(**overrides))

    assert response.status_code == 422, response.text
    assert code(response) == expected
    _assert_nothing_written(api, url)


def test_inactive_location_is_rejected(api, url, fake_locations) -> None:
    fake_locations.records[CITY_ID] = LocationRecord(
        id=CITY_ID, status="INACTIVE", country_id=COLOMBIA_ID, administrative_division_id=DIVISION_ID
    )

    response = api.post(url, json=profile_payload())

    assert response.status_code == 422
    assert code(response) == "LOCATION_INACTIVE"
    assert response.json()["field"] == "city_id"


def test_incoherent_city_is_rejected(api, url, fake_locations) -> None:
    other_division = uuid4()
    fake_locations.records[other_division] = LocationRecord(id=other_division, status="ACTIVE", country_id=COLOMBIA_ID)

    response = api.post(url, json=profile_payload(administrative_division_id=str(other_division)))

    assert response.status_code == 422
    assert code(response) == "GEOGRAPHY_INCOHERENT"
    assert response.json()["field"] == "city_id"


@pytest.mark.parametrize(
    "outcome, expected",
    [("COMPANY_NOT_FOUND", "COMPANY_NOT_FOUND"), ("COMPANY_INACTIVE", "COMPANY_INACTIVE")],
)
def test_invalid_company_reference(api, url, fake_membership, outcome, expected) -> None:
    fake_membership.outcome = outcome

    response = api.post(url, json=profile_payload())

    assert response.status_code == 422
    assert code(response) == expected
    _assert_nothing_written(api, url)


@pytest.mark.parametrize("reason", ["USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE"])
def test_invalid_membership_carries_reason(api, url, fake_membership, reason) -> None:
    fake_membership.outcome = reason

    response = api.post(url, json=profile_payload())

    assert response.status_code == 422
    assert code(response) == "CONFIRMATION_MEMBERSHIP_INVALID"
    assert response.json()["reason"] == reason
    _assert_nothing_written(api, url)


def test_platform_administrator_without_membership_cannot_confirm(api, api_as, url, fake_membership) -> None:
    """RC-15: el alcance de plataforma no sustituye la membresía."""
    fake_membership.outcome = "USER_NOT_MEMBER"
    admin = api_as(
        "perm:all:all:all",
        "perm:operational-context:platform:administer",
        sub="admin-test-sub",
    )

    response = admin.post(url, json=profile_payload())

    assert response.status_code == 422
    assert code(response) == "CONFIRMATION_MEMBERSHIP_INVALID"
    assert response.json()["reason"] == "USER_NOT_MEMBER"
    assert fake_membership.calls == [(COMPANY_ID, "admin-test-sub")]


@pytest.mark.parametrize(
    "setup, dependency",
    [
        (lambda locations, membership: setattr(locations, "mode", "unavailable"), "geography"),
        (lambda locations, membership: setattr(membership, "outcome", "unavailable"), "operational-context"),
        (lambda locations, membership: setattr(membership, "outcome", "keycloak"), "keycloak"),
    ],
)
def test_dependency_unavailable_is_503_without_writing(
    api, url, fake_locations, fake_membership, setup, dependency
) -> None:
    setup(fake_locations, fake_membership)

    response = api.post(url, json=profile_payload())

    assert response.status_code == 503
    assert code(response) == "DEPENDENCY_UNAVAILABLE"
    assert response.json()["dependency"] == dependency
    _assert_nothing_written(api, url)


def test_user_without_operational_context_permissions_confirms(api_as, api, url, fake_membership) -> None:
    """SC-011: la membresía la comprueba el cliente técnico; el usuario no necesita permisos de OC."""
    supervisor = api_as(
        "perm:party-identity:organization_contact_profiles:create",
        "perm:party-identity:organization_contact_profiles:read",
        sub="supervisor-sub",
    )

    response = supervisor.post(url, json=profile_payload())

    assert response.status_code == 201, response.text
    assert fake_membership.calls == [(COMPANY_ID, "supervisor-sub")]
