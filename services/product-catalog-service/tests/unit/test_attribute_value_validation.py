"""Validación de valores tipados (RC-05, FR-046, FR-047)."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from product_catalog_service.domain.attribute_value import ValueTypeMismatch, validate_typed_value

OPTION_ID = uuid4()


@pytest.mark.parametrize(
    ("data_type", "payload", "expected"),
    [
        ("TEXT", {"text_value": "  Rojo "}, ("text_value", "Rojo")),
        ("INTEGER", {"integer_value": 16}, ("integer_value", 16)),
        ("DECIMAL", {"decimal_value": Decimal("1234567890.12345678")}, ("decimal_value", Decimal("1234567890.12345678"))),
        ("BOOLEAN", {"boolean_value": False}, ("boolean_value", False)),
        ("DATE", {"date_value": date(2026, 9, 25)}, ("date_value", date(2026, 9, 25))),
        ("OPTION", {"option_id": OPTION_ID}, ("option_id", OPTION_ID)),
    ],
)
def test_valid_values(data_type: str, payload: dict, expected: tuple) -> None:
    assert validate_typed_value(data_type, payload) == expected


@pytest.mark.parametrize(
    ("data_type", "payload"),
    [
        ("DECIMAL", {"text_value": "3.5"}),
        ("TEXT", {"integer_value": 1}),
        ("TEXT", {"text_value": "   "}),
        ("INTEGER", {"integer_value": 2**63}),
        ("INTEGER", {"integer_value": True}),
        ("DECIMAL", {"decimal_value": Decimal("1.123456789")}),
        ("DECIMAL", {"decimal_value": Decimal("12345678901")}),
        ("DECIMAL", {"decimal_value": Decimal("NaN")}),
        ("BOOLEAN", {"boolean_value": "true"}),
        ("DATE", {"date_value": "2026-02-30"}),
        ("OPTION", {"option_id": "no-uuid"}),
        ("TEXT", {}),
        ("TEXT", {"text_value": "a", "integer_value": 1}),
    ],
)
def test_invalid_values(data_type: str, payload: dict) -> None:
    with pytest.raises(ValueTypeMismatch):
        validate_typed_value(data_type, payload)
