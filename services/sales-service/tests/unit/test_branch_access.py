"""Acceso operativo del usuario (R-02, DS-09; T017)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from sales_service.application.branch_access import require_branch_access, require_membership
from sales_service.application.exceptions import (
    BranchAccessDeniedError,
    DependencyUnavailableError,
    NotFoundError,
)
from sales_service.application.ports import AccessResult

COMPANY, BRANCH, USER = uuid4(), uuid4(), uuid4()


class Directory:
    def __init__(self, result: AccessResult) -> None:
        self.result = result

    def check_branch(self, branch_id):
        return self.result

    def check_company(self, company_id):
        return self.result


def test_allowed_returns_application_user() -> None:
    access = require_branch_access(Directory(AccessResult(True, None, COMPANY, USER)), COMPANY, BRANCH)
    assert access.application_user_id == USER


def test_allowed_in_another_company_is_404() -> None:
    with pytest.raises(NotFoundError):
        require_branch_access(Directory(AccessResult(True, None, uuid4(), USER)), COMPANY, BRANCH)


@pytest.mark.parametrize("reason", ["USER_NOT_MEMBER", "USER_MEMBERSHIP_INACTIVE"])
def test_not_member_is_404(reason) -> None:
    with pytest.raises(NotFoundError):
        require_branch_access(Directory(AccessResult(False, reason, COMPANY, None)), COMPANY, BRANCH)
    with pytest.raises(NotFoundError):
        require_membership(Directory(AccessResult(False, reason, COMPANY, None)), COMPANY)


@pytest.mark.parametrize("reason", ["BRANCH_NOT_ASSIGNED", "USER_BRANCH_INACTIVE", "BRANCH_INACTIVE", "COMPANY_INACTIVE"])
def test_branch_denied_is_403(reason) -> None:
    with pytest.raises(BranchAccessDeniedError):
        require_branch_access(Directory(AccessResult(False, reason, COMPANY, USER)), COMPANY, BRANCH)


def test_branch_of_another_company_is_404() -> None:
    with pytest.raises(NotFoundError):
        require_branch_access(Directory(AccessResult(False, "BRANCH_NOT_ASSIGNED", uuid4(), USER)), COMPANY, BRANCH)


def test_unexpected_reason_is_503() -> None:
    with pytest.raises(DependencyUnavailableError):
        require_branch_access(Directory(AccessResult(False, "OTRA", COMPANY, None)), COMPANY, BRANCH)


def test_membership_allows_inactive_company_for_reads() -> None:
    assert require_membership(Directory(AccessResult(False, "COMPANY_INACTIVE", COMPANY, USER)), COMPANY).application_user_id == USER
