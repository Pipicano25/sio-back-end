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


# Fase B (T010; RC-13, FR-095)


def test_email_keeps_first_char_and_domain() -> None:
    from party_identity_service.domain.masking import mask_email

    assert mask_email("ana@ejemplo.co") == "a***@ejemplo.co"
    assert mask_email("sin-arroba") == "s***"
    assert mask_email(None) is None


def test_phone_keeps_last_two_digits() -> None:
    from party_identity_service.domain.masking import mask_phone

    assert mask_phone("+57 601 555 0123") == "**23"
    assert mask_phone("7") == "*"
    assert mask_phone(None) is None


def test_text_keeps_first_four_chars_and_length() -> None:
    from party_identity_service.domain.masking import mask_text

    assert mask_text("Calle 10 # 20-30") == "Call************"
    assert mask_text("abc") == "***"
    assert mask_text(None) is None
