"""Coherencia del plazo con el tipo de condición de pago (FR-033, FR-034, RN-06).

El `code` del tipo lo entrega Payment Reference en cada validación y nunca se
guarda (Principio III, C-10, DS-06).
"""

from __future__ import annotations

from commercial_relationship_service.domain.errors import PaymentTermsInconsistentError

CASH = "CASH"
CREDIT = "CREDIT"
FINANCING = "FINANCING"

MIN_TERMS_DAYS = 0
MAX_TERMS_DAYS = 3650


def validate_payment_terms(condition_type_code: str, payment_terms_days: int) -> None:
    """`CASH` → `0`; `CREDIT` y `FINANCING` → `> 0`; otros códigos → `≥ 0` (rango 0–3650).

    Raises:
        PaymentTermsInconsistentError: Con el campo `payment_terms_days`.
    """
    if not MIN_TERMS_DAYS <= payment_terms_days <= MAX_TERMS_DAYS:
        raise PaymentTermsInconsistentError(
            f"El plazo debe estar entre {MIN_TERMS_DAYS} y {MAX_TERMS_DAYS} días.",
            field="payment_terms_days",
        )

    if condition_type_code == CASH and payment_terms_days != 0:
        raise PaymentTermsInconsistentError(
            "Una condición de contado exige un plazo de 0 días.", field="payment_terms_days"
        )

    if condition_type_code in {CREDIT, FINANCING} and payment_terms_days <= 0:
        raise PaymentTermsInconsistentError(
            "Una condición de crédito o financiación exige un plazo mayor que 0 días.",
            field="payment_terms_days",
        )
