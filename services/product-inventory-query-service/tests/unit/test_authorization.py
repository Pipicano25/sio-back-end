"""Autorización previa con Operational Context (T078; FR-022-11, FR-022-20 a 23, CP-46 a CP-48, CP-59)."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from product_inventory_query_service.application.authorization import authorize
from product_inventory_query_service.application.exceptions import NotFoundError
from tests.fakes import build_fakes


def test_access_and_branches_go_in_parallel_and_first() -> None:
    fakes = build_fakes()
    company, branches = fakes.oc.add_company(branches=2)
    scope = asyncio.run(authorize(fakes.oc, company, None))
    assert set(scope.branch_ids) == set(branches)
    assert fakes.log.order[:2] == ["operational_access", "branches"]
    assert fakes.log.total() == 2


def test_not_member_or_unknown_company_is_404_without_distinction() -> None:
    fakes = build_fakes()
    not_member, _ = fakes.oc.add_company(member=False)
    errors = []
    for company in (not_member, uuid4()):
        with pytest.raises(NotFoundError) as exc:
            asyncio.run(authorize(fakes.oc, company, None))
        errors.append(exc.value.message)
    assert len(set(errors)) == 1


def test_company_scope_uses_only_active_branches_and_inactive_only_explicitly() -> None:
    fakes = build_fakes()
    company, branches = fakes.oc.add_company(branches=2, inactive=1)
    active, inactive = branches[:2], branches[2]
    assert set(asyncio.run(authorize(fakes.oc, company, None)).branch_ids) == set(active)
    scope = asyncio.run(authorize(fakes.oc, company, [inactive, active[0], inactive]))
    assert scope.branch_ids == [inactive, active[0]]


def test_branch_of_another_company_is_404() -> None:
    fakes = build_fakes()
    company, _ = fakes.oc.add_company()
    _, other_branches = fakes.oc.add_company()
    with pytest.raises(NotFoundError):
        asyncio.run(authorize(fakes.oc, company, [other_branches[0]]))


def test_branch_not_assigned_to_the_user_is_allowed() -> None:
    """A-08: con membresía y permiso de lectura, cualquier sucursal de la empresa; no se consulta la asignación."""
    fakes = build_fakes()
    company, branches = fakes.oc.add_company(branches=3)
    scope = asyncio.run(authorize(fakes.oc, company, [branches[2]]))
    assert scope.branch_ids == [branches[2]]
    assert all(name in {"operational_access", "branches"} for name in fakes.log.order)


def test_dependency_failure_propagates() -> None:
    from product_inventory_query_service.application.exceptions import DependencyUnavailableError

    fakes = build_fakes()
    company, _ = fakes.oc.add_company()
    fakes.oc.fail.add("operational_access")
    with pytest.raises(DependencyUnavailableError):
        asyncio.run(authorize(fakes.oc, company, None))
