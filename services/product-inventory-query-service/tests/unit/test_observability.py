"""Logs sin secretos (T005; FR-022-75, FR-022-77)."""

from __future__ import annotations

import logging

from product_inventory_query_service.observability import (
    REDACTED,
    SERVICE_LOGGER,
    build_traceparent,
    configure_logging,
    redact,
)

TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.c2lnbmF0dXJlLXRlc3Q"
CURSOR = "v1.eyJ2IjoxLCJjaWQiOiJ4In0.QWJjZGVmZ2hpamtsbW5vcA"


def test_redact_removes_tokens_cursors_and_refs() -> None:
    text = f"Authorization: Bearer {TOKEN} cursor={CURSOR} url=/api/v1/public/product-images?ref=AAAA.BBBB raw {CURSOR}"
    cleaned = redact(text)
    assert TOKEN not in cleaned
    assert CURSOR not in cleaned
    assert "AAAA.BBBB" not in cleaned
    assert REDACTED in cleaned


def test_log_records_never_contain_secrets(caplog) -> None:
    configure_logging()
    logger = logging.getLogger(SERVICE_LOGGER)
    logger.propagate = True
    try:
        with caplog.at_level(logging.INFO, logger=SERVICE_LOGGER):
            logger.info("llamada con token %s y cursor %s", f"Bearer {TOKEN}", CURSOR)
    finally:
        logger.propagate = False
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert TOKEN not in joined
    assert CURSOR not in joined


def test_traceparent_keeps_trace_id_and_uses_new_span() -> None:
    trace = "4bf92f3577b34da6a3ce929d0e0e4736"
    first, second = build_traceparent(trace), build_traceparent(trace)
    assert first.split("-")[1] == trace
    assert first.split("-")[2] != second.split("-")[2]
