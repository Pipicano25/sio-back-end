"""Validación del cursor paso a paso (T089; FR-022-147, FR-022-149, FR-022-150, CP-112 a CP-120)."""

from __future__ import annotations

import logging
from dataclasses import replace
from uuid import uuid4

import pytest

from product_inventory_query_service.application.exceptions import InvalidCursorError
from product_inventory_query_service.domain.cursor import CursorCodec, Decision, Expected, ResetReason

SECRET = "cursor-secret-for-tests-only-0123456789abcdef"
COMPANY = str(uuid4())
EXPECTED = Expected("product-overviews", COMPANY, "huella-colgate", "display_name:asc", 20, "R-B")
POSITION = {"k": ["Crema"], "id": str(uuid4())}


def codec(now: float) -> CursorCodec:
    return CursorCodec(SECRET, ttl_seconds=900, clock=lambda: now)


def cursor(**changes) -> str:
    return codec(1000.0).issue(replace(EXPECTED, **changes), kind="PAGE", position=POSITION)


def test_no_cursor_is_first_page() -> None:
    assert codec(1000.0).evaluate(None, EXPECTED).decision is Decision.FIRST


def test_matching_cursor_continues() -> None:
    result = codec(1000.0).evaluate(cursor(), EXPECTED)
    assert result.decision is Decision.CONTINUE and result.payload.pos == POSITION


def test_other_company_and_other_endpoint_are_invalid_with_the_same_public_message() -> None:
    messages = set()
    for text in (cursor(company_id=str(uuid4())), cursor(endpoint="inventory-overviews"), "v1.basura.firma"):
        with pytest.raises(InvalidCursorError) as exc:
            codec(1000.0).evaluate(text, EXPECTED)
        messages.add(exc.value.message)
    assert len(messages) == 1


def test_expiry_at_900_seconds_plus_30_of_tolerance() -> None:
    text = cursor()
    assert codec(1000.0 + 900 + 30).evaluate(text, EXPECTED).decision is Decision.CONTINUE
    expired = codec(1000.0 + 900 + 31).evaluate(text, EXPECTED)
    assert (expired.decision, expired.reason) == (Decision.RESET, ResetReason.CURSOR_EXPIRED)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"fingerprint": "huella-abrilar"}, ResetReason.FILTERS_CHANGED),
        ({"sort": "internal_code:asc"}, ResetReason.SORT_CHANGED),
        ({"page_size": 10}, ResetReason.PAGE_SIZE_CHANGED),
    ],
)
def test_legitimate_changes_reset_without_error(changes, reason) -> None:
    result = codec(1000.0).evaluate(cursor(), replace(EXPECTED, **changes))
    assert (result.decision, result.reason) == (Decision.RESET, reason)


def test_several_changes_report_the_first_in_the_table_order() -> None:
    result = codec(1000.0).evaluate(cursor(), replace(EXPECTED, fingerprint="otra", sort="created_at:asc", page_size=5))
    assert result.reason is ResetReason.FILTERS_CHANGED
    result = codec(1000.0).evaluate(cursor(), replace(EXPECTED, sort="created_at:asc", page_size=5))
    assert result.reason is ResetReason.SORT_CHANGED
    expired = codec(5000.0).evaluate(cursor(), replace(EXPECTED, fingerprint="otra"))
    assert expired.reason is ResetReason.CURSOR_EXPIRED


def test_other_route_with_everything_else_equal_is_invalid_and_logged(caplog) -> None:
    logger = logging.getLogger("product_inventory_query_service")
    logger.propagate = True
    try:
        with caplog.at_level(logging.ERROR, logger="product_inventory_query_service"):
            with pytest.raises(InvalidCursorError):
                codec(1000.0).evaluate(cursor(route="R-C"), EXPECTED)
    finally:
        logger.propagate = False
    assert "determinista" in caplog.text


def test_tampered_cursor_is_rejected_before_reading_its_company() -> None:
    text = cursor(company_id=str(uuid4()))
    tampered = text[:-2] + ("AA" if not text.endswith("AA") else "BB")
    with pytest.raises(InvalidCursorError) as exc:
        codec(1000.0).evaluate(tampered, EXPECTED)
    assert exc.value.cause == "firma"
