"""Normalización de dominio de la Fase B (T020; FR-014, FR-015, FR-078, DS-13)."""

from uuid import uuid4

import pytest

from party_identity_service.domain.business_sector import normalize_code
from party_identity_service.domain.contact import (
    ContactData,
    normalize_email,
    normalize_optional_text,
)
from party_identity_service.domain.legal_representative import (
    is_primary_type,
    normalize_document_reference,
)


def test_optional_text_is_trimmed_and_empty_becomes_none() -> None:
    assert normalize_optional_text("  Calle 1  ") == "Calle 1"
    assert normalize_optional_text("   ") is None
    assert normalize_optional_text(None) is None


def test_email_is_trimmed_and_lowercased() -> None:
    assert normalize_email("  Ana@Ejemplo.CO ") == "ana@ejemplo.co"
    assert normalize_email("") is None


def test_contact_data_normalization_enables_semantic_comparison() -> None:
    country = uuid4()
    first = ContactData.normalized(
        email="ANA@EJEMPLO.CO", phone=" 300 ", address_line=None,
        country_id=country, administrative_division_id=None, city_id=None, postal_code="",
    )
    second = ContactData.normalized(
        email="ana@ejemplo.co", phone="300", address_line="  ",
        country_id=country, administrative_division_id=None, city_id=None, postal_code=None,
    )

    assert first == second
    assert first.has_contact


def test_contact_data_without_email_phone_or_address_has_no_contact() -> None:
    data = ContactData.normalized(
        email=None, phone="  ", address_line=None,
        country_id=uuid4(), administrative_division_id=None, city_id=None, postal_code="110111",
    )

    assert not data.has_contact


@pytest.mark.parametrize("value, expected", [("  a01 ", "A01"), ("ciiu_rev4_ac", "CIIU_REV4_AC")])
def test_sector_codes_are_normalized(value: str, expected: str) -> None:
    assert normalize_code(value) == expected


def test_document_reference_is_trimmed_and_blank_becomes_none() -> None:
    assert normalize_document_reference("  Escritura 123  ") == "Escritura 123"
    assert normalize_document_reference("   ") is None


def test_is_primary_is_derived_from_type() -> None:
    assert is_primary_type("PRIMARY") is True
    assert is_primary_type("ALTERNATE") is False
    assert is_primary_type("OTHER") is False
