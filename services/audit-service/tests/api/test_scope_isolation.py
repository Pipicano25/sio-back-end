"""Aislamiento por empresa y dependencia de Operational Context (RC-07, RC-08, RC-10, FR-037, FR-050; T038)."""

from __future__ import annotations

import pytest

from tests.api.helpers import register
from tests.conftest import user_sub


def url(company) -> str:
    return f"/api/v1/companies/{company}/audit-events"


def test_non_member_gets_404(as_user, emitter, other_company) -> None:
    event = register(emitter, company_id=str(other_company))
    admin = as_user("admin.test")

    assert admin.get(url(other_company)).status_code == 404
    assert admin.get(f"{url(other_company)}/{event['id']}").status_code == 404
    history = admin.get(f"/api/v1/companies/{other_company}/entity-history/PriceListItem/{event['entity_id']}")
    assert history.status_code == 404


def test_company_route_never_returns_platform_or_other_company(as_user, emitter, company, fake_oc) -> None:
    other = __import__("uuid").uuid4()
    fake_oc.add_member(user_sub("admin.test"), other)
    mine = register(emitter, company_id=str(company))
    register(emitter, company_id=str(other))
    platform = register(emitter, company_id=None, entity_type="GlobalProduct")

    admin = as_user("admin.test")
    items = admin.get(url(company), params={"page_size": 100}).json()["items"]

    assert [item["id"] for item in items] == [mine["id"]]
    assert admin.get(f"{url(company)}/{platform['id']}").status_code == 404


@pytest.mark.parametrize("username", ["compras.test", "ventas.test", "inventario.test", "reportes.test", "consulta.test"])
def test_membership_does_not_grant_audit(as_user, company, username) -> None:
    """FR-037: ser miembro no da acceso; sin `perm:audit:audit-events:read` → 403."""
    response = as_user(username).get(url(company))
    assert response.status_code == 403
    assert response.json()["code"] == "AUDIT.FORBIDDEN"


def test_audit_read_without_operational_context_permission(as_user, company, fake_oc) -> None:
    """FR-037: `audit-events:read` sin `application_users:read` → OC 403 → acceso denegado controlado."""
    fake_oc.forbidden_subjects.add(user_sub("auditor.sin-oc"))

    response = as_user("auditor.sin-oc").get(url(company))

    assert response.status_code == 403
    body = response.json()
    assert body["code"] == "AUDIT.OPERATIONAL_ACCESS_DENIED"
    assert "items" not in body
    assert "perm:" not in response.text


def test_user_token_is_propagated_never_a_technical_one(as_user, user_token, company, fake_oc) -> None:
    """FR-050: Operational Context recibe el `Authorization` del usuario que consulta."""
    as_user("supervisor.test").get(url(company))

    assert fake_oc.calls == [(user_sub("supervisor.test"), f"Bearer {user_token('supervisor.test')}", company)]


def test_operational_context_unavailable(as_user, company, fake_oc) -> None:
    fake_oc.unavailable = True

    response = as_user("admin.test").get(url(company))

    assert response.status_code == 503
    assert response.json()["code"] == "AUDIT.DEPENDENCY_UNAVAILABLE"
    assert response.json()["dependency"] == "operational-context"
    # La plataforma no depende de Operational Context.
    assert as_user("admin.test").get("/api/v1/platform-audit-events").status_code == 200


def test_membership_checked_on_every_request(as_user, company, fake_oc) -> None:
    admin = as_user("admin.test")
    admin.get(url(company))
    admin.get(url(company))
    assert len(fake_oc.calls) == 2
