"""`AccessScope`: capacidades de plataforma y alcance por membresía (R-01, R-02, RC-03)."""

from uuid import uuid4

import pytest
from sio_auth.permissions import extract_permission_grants

from operational_context_service.application.access_scope import AccessScope
from operational_context_service.application.exceptions import NotFoundError


def _scope(*roles, members=()):
    return AccessScope.build(
        subject="user-1",
        grants=extract_permission_grants(roles),
        member_company_ids=members,
    )


def test_explicit_platform_permissions():
    admin = _scope("perm:operational-context:platform:administer")
    lookup = _scope("perm:operational-context:platform:lookup")

    assert admin.is_platform_admin and not admin.can_lookup
    assert lookup.can_lookup and not lookup.is_platform_admin


@pytest.mark.parametrize(
    "role",
    [
        "perm:all:all:all",
        "perm:operational-context:all:all",
        "perm:operational-context:platform:all",
    ],
)
def test_action_wildcards_grant_platform_capabilities(role):
    scope = _scope(role)

    assert scope.is_platform_admin and scope.can_lookup


@pytest.mark.parametrize(
    "role",
    [
        "perm:all:all:read",
        "perm:all:all:create",
        "perm:all:all:update",
        "perm:all:all:delete",
        "perm:operational-context:all:read",
        "perm:operational-context:all:update",
        "perm:operational-context:companies:read",
    ],
)
def test_crud_wildcards_do_not_grant_platform(role):
    scope = _scope(role)

    assert not scope.is_platform_admin and not scope.can_lookup


def test_membership_scope_hides_other_companies_with_same_not_found():
    own, other = uuid4(), uuid4()
    scope = _scope("perm:operational-context:all:read", members=[own])

    scope.ensure_company_visible(own)

    with pytest.raises(NotFoundError) as error:
        scope.ensure_company_visible(other)

    assert error.value.code == "NOT_FOUND"
    assert error.value.message == "La empresa solicitada no existe."


def test_platform_sees_everything_and_has_no_filter():
    scope = _scope("perm:all:all:all")

    scope.ensure_company_visible(uuid4())
    assert scope.company_filter() is None


def test_member_filter_is_the_active_memberships():
    own = uuid4()
    scope = _scope("perm:operational-context:all:read", members=[own])

    assert scope.company_filter() == frozenset({own})


def test_lookup_only_widens_reads_by_uuid():
    scope = _scope("perm:operational-context:platform:lookup")
    company = uuid4()

    scope.ensure_company_visible(company, lookup_read=True)

    with pytest.raises(NotFoundError):
        scope.ensure_company_visible(company)

    assert scope.company_filter() == frozenset()
