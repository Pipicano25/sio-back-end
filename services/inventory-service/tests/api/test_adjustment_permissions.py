"""Autorización de ajustes: humanos con permiso, membresía y sucursal activa (RC-11; DS-04, DS-14; T035)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.conftest import ADJUSTMENTS_CREATE, line, operation_body, user_sub

ENTRIES = "/api/v1/inventory-entries"


def url(company) -> str:
    return f"/api/v1/companies/{company}/inventory-adjustments"


def body(world, *, branch=None, product=None):
    return {
        "adjustment_key": str(uuid4()),
        "branch_id": str(branch or world.branch),
        "company_product_id": str(product or world.products[0]),
        "adjustment_type": "POSITIVE",
        "quantity": "1",
        "unit_cost": "10",
        "reason": "Ajuste ficticio de validación",
    }


@pytest.fixture(autouse=True)
def stock(operator, world):
    assert operator.post(ENTRIES, json=operation_body(world, line(world.products[0], "5", unit_cost="10"))).status_code == 201


def test_service_account_with_wildcard_is_forbidden(as_token, service_token, world) -> None:
    for roles in (("perm:all:all:all",), (ADJUSTMENTS_CREATE,)):
        response = as_token(service_token(*roles)).post(url(world.company), json=body(world))
        assert response.status_code == 403
        assert response.json()["code"] == "INVENTORY.FORBIDDEN"


def test_human_without_permission_is_forbidden(as_user, world) -> None:
    for username in ("sin-permisos.test",):
        assert as_user(username).post(url(world.company), json=body(world)).status_code == 403


def test_admin_with_wildcard_and_assignment_can_adjust(as_user, world) -> None:
    assert as_user("admin.sio").post(url(world.company), json=body(world)).status_code == 201


@pytest.mark.parametrize("status", ["INACTIVE"])
def test_inactive_membership_is_not_found(as_user, world, fake_oc, status) -> None:
    fake_oc.add_member(user_sub("operario.dao"), world.company, status=status)
    assert as_user("operario.dao").post(url(world.company), json=body(world)).status_code == 404


def test_non_member_is_not_found(as_user, world, fake_oc) -> None:
    fake_oc.member_status.pop((user_sub("operario.dao"), world.company))
    fake_oc.members.discard((user_sub("operario.dao"), world.company))
    assert as_user("operario.dao").post(url(world.company), json=body(world)).status_code == 404


@pytest.mark.parametrize("case", ["not_assigned", "assignment_inactive"])
def test_assignment_does_not_limit_branch_access(as_user, world, fake_oc, case) -> None:
    """Acceso por membresía (2026-11-19): sin asignación o con la asignación inactiva se ajusta igual."""
    branch = world.branch
    if case == "not_assigned":
        branch = world.other_branch
    else:
        fake_oc.assign(user_sub("operario.dao"), world.branch, status="INACTIVE")
    response = as_user("operario.dao").post(url(world.company), json=body(world, branch=branch))
    assert response.status_code == 201, response.text


@pytest.mark.parametrize("case", ["branch_inactive", "company_inactive"])
def test_branch_access_denied(as_user, world, fake_oc, case) -> None:
    """Acceso por membresía (2026-11-19): `BRANCH_ACCESS_DENIED` solo por sucursal o empresa inactiva."""
    sub = user_sub("operario.dao")
    if case == "branch_inactive":
        branch = fake_oc.add_branch(world.company, status="INACTIVE")
        fake_oc.assign(sub, branch)
    else:
        branch = fake_oc.add_branch(world.company, company_status="INACTIVE")
        fake_oc.assign(sub, branch)
    response = as_user("operario.dao").post(url(world.company), json=body(world, branch=branch))
    assert response.status_code == 403
    assert response.json()["code"] == "INVENTORY.BRANCH_ACCESS_DENIED"


def test_branch_of_another_company_is_not_found(as_user, world, fake_oc) -> None:
    fake_oc.add_member(user_sub("operario.dao"), world.other_company)
    fake_oc.assign(user_sub("operario.dao"), world.other_company_branch)
    response = as_user("operario.dao").post(url(world.company), json=body(world, branch=world.other_company_branch))
    assert response.status_code == 404


def test_operational_access_denied_and_unavailable(as_user, world, fake_oc) -> None:
    fake_oc.forbidden_subjects.add(user_sub("operario.dao"))
    response = as_user("operario.dao").post(url(world.company), json=body(world))
    assert (response.status_code, response.json()["code"]) == (403, "INVENTORY.OPERATIONAL_ACCESS_DENIED")
    fake_oc.forbidden_subjects.clear()
    fake_oc.unavailable = True
    response = as_user("operario.dao").post(url(world.company), json=body(world))
    assert (response.status_code, response.json()["dependency"]) == (503, "operational-context")


def test_branch_access_uses_the_user_token(as_user, world, fake_oc) -> None:
    as_user("operario.dao").post(url(world.company), json=body(world))
    sub, authorization, branch = fake_oc.branch_access_calls[-1]
    # El `sub` sale del token propagado (`Authorization` del usuario, nunca el técnico).
    assert (sub, branch) == (user_sub("operario.dao"), world.branch)
    assert authorization.startswith("Bearer ")
