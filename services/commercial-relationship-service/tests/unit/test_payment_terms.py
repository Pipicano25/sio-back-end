"""Coherencia plazo–tipo de condición de pago (T005; FR-033, FR-034, RN-06)."""

from __future__ import annotations

import pytest

from commercial_relationship_service.domain.errors import PaymentTermsInconsistentError
from commercial_relationship_service.domain.payment_terms import validate_payment_terms


@pytest.mark.parametrize(
    ("code", "days"),
    [("CASH", 0), ("CREDIT", 30), ("FINANCING", 60), ("CREDIT", 3650), ("OTHER", 0), ("OTHER", 15)],
)
def test_consistent_terms(code, days):
    validate_payment_terms(code, days)


@pytest.mark.parametrize(
    ("code", "days"),
    [("CASH", 15), ("CREDIT", 0), ("FINANCING", 0), ("CREDIT", 3651), ("OTHER", -1)],
)
def test_inconsistent_terms(code, days):
    with pytest.raises(PaymentTermsInconsistentError) as error:
        validate_payment_terms(code, days)
    assert error.value.field == "payment_terms_days"
