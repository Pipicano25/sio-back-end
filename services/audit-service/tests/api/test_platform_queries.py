"""Eventos de plataforma con permiso independiente (FR-034, FR-036, RC-10; T039)."""

from __future__ import annotations

import pytest

from tests.api.helpers import register
from tests.conftest import PLATFORM_READ, READ, user_sub


@pytest.fixture
def platform_reader(as_token, make_token):
    return as_token(make_token(PLATFORM_READ, sub="sub-plataforma", preferred_username="plataforma"))


def test_only_platform_events_without_membership(platform_reader, emitter, company, fake_oc) -> None:
    platform = register(emitter, company_id=None, entity_type="GlobalProduct")
    register(emitter, company_id=str(company))
    fake_oc.fail_if_called = True

    response = platform_reader.get("/api/v1/platform-audit-events")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [platform["id"]]
    assert platform_reader.get(f"/api/v1/platform-audit-events/{platform['id']}").json() == platform


def test_company_event_by_platform_route_is_404(platform_reader, emitter, company) -> None:
    event = register(emitter, company_id=str(company))
    assert platform_reader.get(f"/api/v1/platform-audit-events/{event['id']}").status_code == 404


def test_company_permission_alone_cannot_see_platform(as_user) -> None:
    assert as_user("auditor.sin-oc").get("/api/v1/platform-audit-events").status_code == 403


def test_platform_permission_alone_cannot_see_company(platform_reader, company, fake_oc) -> None:
    fake_oc.add_member("sub-plataforma", company)
    assert platform_reader.get(f"/api/v1/companies/{company}/audit-events").status_code == 403


def test_wildcards_give_platform_access(as_user) -> None:
    for username in ("admin.test", "supervisor.test"):
        assert as_user(username).get("/api/v1/platform-audit-events").status_code == 200


def test_platform_query_has_no_branch_filter(platform_reader) -> None:
    from uuid import uuid4

    response = platform_reader.get("/api/v1/platform-audit-events", params={"branch_id": str(uuid4())})
    assert response.status_code == 422


def test_both_permissions_keep_scopes_apart(as_token, make_token, emitter, company, fake_oc) -> None:
    client = as_token(make_token(READ, PLATFORM_READ, sub=user_sub("ambos"), preferred_username="ambos"))
    fake_oc.add_member(user_sub("ambos"), company)
    mine = register(emitter, company_id=str(company))
    platform = register(emitter, company_id=None)

    assert [i["id"] for i in client.get(f"/api/v1/companies/{company}/audit-events").json()["items"]] == [mine["id"]]
    assert [i["id"] for i in client.get("/api/v1/platform-audit-events").json()["items"]] == [platform["id"]]
