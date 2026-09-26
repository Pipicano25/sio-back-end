"""Pruebas del enmascaramiento de datos sensibles (DS-09, R-11)."""

from datetime import date

from party_identity_service.domain.masking import (
    mask_birth_date,
    mask_identification_number,
)


def test_identification_number_keeps_last_four() -> None:
    assert mask_identification_number("1000000000") == "******0000"


def test_short_identification_number_is_fully_masked() -> None:
    assert mask_identification_number("1234") == "****"
    assert mask_identification_number("12") == "**"


def test_none_is_preserved() -> None:
    assert mask_identification_number(None) is None
    assert mask_birth_date(None) is None


def test_birth_date_is_fully_masked() -> None:
    assert mask_birth_date(date(1990, 5, 10)) == "****-**-**"
