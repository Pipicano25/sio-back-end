"""Normalización de códigos, nombres e identificadores (RC-01, FR-003, FR-004, R-17)."""

import pytest

from product_catalog_service.application.exceptions import ValidationError
from product_catalog_service.application.normalization import (
    canonical_name_key,
    normalize_code,
    normalize_identifier_value,
    normalize_name,
)


def test_normalize_code_strips_and_uppercases() -> None:
    assert normalize_code(" kg ", max_length=20) == "KG"


@pytest.mark.parametrize("value", ["", "   "])
def test_normalize_code_rejects_blank(value: str) -> None:
    with pytest.raises(ValidationError):
        normalize_code(value, max_length=20)


def test_normalize_code_rejects_too_long() -> None:
    with pytest.raises(ValidationError):
        normalize_code("X" * 21, max_length=20)


def test_normalize_name_collapses_spaces() -> None:
    assert normalize_name("  Arroz   blanco ", max_length=200) == "Arroz blanco"


def test_normalize_name_rejects_blank() -> None:
    with pytest.raises(ValidationError):
        normalize_name("   ", max_length=10)


def test_canonical_name_key_removes_accents_case_and_spaces() -> None:
    assert canonical_name_key("Árroz  BLANCO") == "arroz blanco"


def test_normalize_identifier_value_keeps_leading_zeros() -> None:
    assert normalize_identifier_value(" 000-123 45 ") == "00012345"
