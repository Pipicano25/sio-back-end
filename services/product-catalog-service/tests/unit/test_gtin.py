"""Reglas de la familia GTIN (RC-07, FR-056, FR-056a, FR-057b)."""

import pytest

from product_catalog_service.domain.gtin import (
    canonical_value,
    gtin_canonical,
    has_valid_check_digit,
    is_valid_gtin_format,
)


@pytest.mark.parametrize(
    "value",
    ["96385074", "036000291452", "4006381333931", "7702004003508", "10036000291459"],
)
def test_valid_check_digits(value: str) -> None:
    assert has_valid_check_digit(value)
    assert is_valid_gtin_format(value)


@pytest.mark.parametrize("value", ["96385075", "036000291453", "4006381333932"])
def test_invalid_check_digits(value: str) -> None:
    assert not has_valid_check_digit(value)
    assert not is_valid_gtin_format(value)


@pytest.mark.parametrize("value", ["12345", "ABCDEFGH1234", "123456789012345", "0360002914 52"])
def test_invalid_gtin_shape(value: str) -> None:
    assert not is_valid_gtin_format(value)


def test_upc_ean_gtin_share_canonical_form() -> None:
    assert (
        gtin_canonical("036000291452")
        == gtin_canonical("0036000291452")
        == gtin_canonical("00036000291452")
        == "00036000291452"
    )


def test_canonical_value_only_pads_gtin_family() -> None:
    assert canonical_value("UPC", "036000291452") == "00036000291452"
    assert canonical_value("BARCODE", "ABC123") == "ABC123"
    assert canonical_value("OTHER", "12") == "12"
