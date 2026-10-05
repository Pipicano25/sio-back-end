"""Reglas de transición de `GlobalPaymentConditionType` (RC-04; FR-012 a FR-014)."""

from __future__ import annotations

import pytest

from payment_reference_service.application.exceptions import InvalidStatusTransitionError
from payment_reference_service.domain.global_payment_condition_types import (
    PaymentConditionStatus,
    deactivated_status,
    reactivated_status,
)


def test_active_can_be_deactivated():
    assert deactivated_status(PaymentConditionStatus.ACTIVE) is PaymentConditionStatus.INACTIVE


def test_inactive_can_be_reactivated():
    assert reactivated_status(PaymentConditionStatus.INACTIVE) is PaymentConditionStatus.ACTIVE


def test_deactivating_an_inactive_type_is_invalid():
    with pytest.raises(InvalidStatusTransitionError):
        deactivated_status(PaymentConditionStatus.INACTIVE)


def test_reactivating_an_active_type_is_invalid():
    with pytest.raises(InvalidStatusTransitionError):
        reactivated_status(PaymentConditionStatus.ACTIVE)
