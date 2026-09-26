"""Reglas puras del acceso operativo (RC-07; `domain/access.py`)."""

import itertools

import pytest

from operational_context_service.domain.access import (
    AccessDenialReason as R,
    AccessFacts,
    evaluate_own_access,
    evaluate_technical_access,
)

A, I = "ACTIVE", "INACTIVE"


def facts(company=A, branch=A, membership=A, assignment=A, permission=None, branch_requested=True):
    granted = None if permission is None else (lambda: permission)
    return AccessFacts(
        company_status=company,
        branch_requested=branch_requested,
        branch_status=branch,
        membership_status=membership,
        user_branch_status=assignment,
        permission_granted=granted,
    )


def test_everything_active_is_allowed():
    assert evaluate_own_access(facts()) is None
    assert evaluate_technical_access(facts(permission=True)) is None


@pytest.mark.parametrize(
    ("overrides", "own", "technical"),
    [
        ({"membership": None}, R.USER_NOT_MEMBER, R.USER_NOT_MEMBER),
        ({"membership": I}, R.USER_MEMBERSHIP_INACTIVE, R.USER_MEMBERSHIP_INACTIVE),
        ({"company": I}, R.COMPANY_INACTIVE, R.COMPANY_INACTIVE),
        ({"branch": I}, R.BRANCH_INACTIVE, R.BRANCH_INACTIVE),
        ({"assignment": None}, R.BRANCH_NOT_ASSIGNED, R.BRANCH_NOT_ASSIGNED),
        ({"assignment": I}, R.USER_BRANCH_INACTIVE, R.USER_BRANCH_INACTIVE),
        ({"permission": False}, R.PERMISSION_DENIED, R.PERMISSION_DENIED),
        # Varias fallas: la causa es la primera en el orden de cada vía.
        ({"company": I, "membership": None}, R.USER_NOT_MEMBER, R.COMPANY_INACTIVE),
        ({"branch": I, "membership": I}, R.USER_MEMBERSHIP_INACTIVE, R.BRANCH_INACTIVE),
        ({"company": I, "branch": I}, R.COMPANY_INACTIVE, R.COMPANY_INACTIVE),
    ],
)
def test_first_failing_condition_is_the_reason(overrides, own, technical):
    assert evaluate_own_access(facts(**overrides)) is own
    assert evaluate_technical_access(facts(**overrides)) is technical


def test_own_way_does_not_distinguish_unknown_resources():
    assert evaluate_own_access(facts(company=None, membership=None)) is R.USER_NOT_MEMBER
    assert evaluate_own_access(facts(branch=None, membership=A)) is R.USER_NOT_MEMBER


def test_company_level_ignores_branch_conditions():
    company_only = facts(branch=None, assignment=None, branch_requested=False)

    assert evaluate_own_access(company_only) is None
    assert evaluate_technical_access(company_only) is None


def test_permission_is_evaluated_last_and_only_if_needed():
    calls = []

    def granted():
        calls.append(1)
        return True

    blocked = AccessFacts(
        company_status=I,
        branch_requested=False,
        branch_status=None,
        membership_status=A,
        user_branch_status=None,
        permission_granted=granted,
    )

    assert evaluate_technical_access(blocked) is R.COMPANY_INACTIVE
    assert calls == []


def test_any_single_failing_condition_denies_access():
    """Tabla completa: acceso solo si todo está ACTIVE y el permiso se concede."""
    options = {
        "company": [A, I],
        "branch": [A, I],
        "membership": [A, I, None],
        "assignment": [A, I, None],
        "permission": [None, True, False],
    }
    for values in itertools.product(*options.values()):
        case = dict(zip(options, values))
        expected_allowed = (
            case["company"] == case["branch"] == case["membership"] == case["assignment"] == A
            and case["permission"] is not False
        )
        assert (evaluate_own_access(facts(**case)) is None) == expected_allowed, case
        assert (evaluate_technical_access(facts(**case)) is None) == expected_allowed, case
