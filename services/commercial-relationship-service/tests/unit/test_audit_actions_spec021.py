"""Acciones de auditoría de la spec 021 (FR-021-33; T012): formato del contrato v1 de `sio-audit`."""

from __future__ import annotations

import re

import pytest

from commercial_relationship_service.application import audit_actions as actions

SPEC_021 = (
    "CREATE_PRICING_POLICY", "UPDATE_PRICING_POLICY", "CHANGE_PRICING_POLICY_PERCENTAGE",
    "ASSIGN_PRICING_POLICY_PRESENTATION", "UNASSIGN_PRICING_POLICY_PRESENTATION", "DEACTIVATE_PRICING_POLICY",
    "UPDATE_COMPANY_PRODUCT_PURCHASE_TAX", "RECEIVE_AUTOMATIC_PRICE_REQUEST", "RESOLVE_AUTOMATIC_PRICE",
    "APPLY_AUTOMATIC_PRICE", "SKIP_AUTOMATIC_PRICE", "END_PRICE_WITHOUT_POLICY", "CANCEL_FUTURE_PRICE",
    "FAIL_AUTOMATIC_PRICE",
)


@pytest.mark.parametrize("name", SPEC_021)
def test_action_exists_and_matches_contract(name: str) -> None:
    assert getattr(actions, name) == name
    assert re.fullmatch(r"[A-Z][A-Z0-9_]{0,49}", name)


def test_process_actions_are_not_http_actions() -> None:
    assert set(actions.PROCESS_ACTIONS) == {
        "APPLY_AUTOMATIC_PRICE", "SKIP_AUTOMATIC_PRICE", "END_PRICE_WITHOUT_POLICY", "FAIL_AUTOMATIC_PRICE",
        "CANCEL_FUTURE_PRICE",
    }
    assert not set(actions.PROCESS_ACTIONS) & set(actions.ACTIONS)
