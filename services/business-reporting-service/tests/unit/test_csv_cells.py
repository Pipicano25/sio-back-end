"""Celdas del CSV: protección de fórmulas solo en texto (OWASP CSV Injection; FR-023-43)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from business_reporting_service.api.csv_stream import Number, cell


@pytest.mark.parametrize("text", ["=1+1", "+57 300", "-x", "@cmd", "\tx", "\rx"])
def test_dangerous_text_is_prefixed(text) -> None:
    assert cell(text) == "'" + text


@pytest.mark.parametrize("text", ["Acetaminofén", "OC-0001", "1+1", "a=b", ""])
def test_safe_text_is_unchanged(text) -> None:
    assert cell(text) == text


def test_numbers_are_never_prefixed() -> None:
    assert cell(Number("-5.00")) == "-5.00" and cell(Number(Decimal("-2.5000"))) == "-2.5000" and cell(Number(3)) == "3"
    assert cell(None) == "" and cell(Number(None)) == ""
