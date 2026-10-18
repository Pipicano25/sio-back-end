"""El log de acceso nunca contiene la referencia firmada de una imagen (spec 022, FR-022-77)."""

from __future__ import annotations

import logging

from product_catalog_service.api.tracing import REDACTED, ImageRefRedactionFilter, configure_logging, redact_image_ref


def test_ref_value_is_redacted_in_uvicorn_access_records() -> None:
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                               ("127.0.0.1:5000", "GET", "/api/v1/public/product-images?ref=AbC_12-x.Yz9-Q", "1.1", 200),
                               None)
    assert ImageRefRedactionFilter().filter(record)
    message = record.getMessage()
    assert "AbC_12-x.Yz9-Q" not in message and f"ref={REDACTED}" in message


def test_other_parameters_and_paths_are_kept() -> None:
    assert redact_image_ref("/api/v1/products?page=2&ref=secreto&page_size=5") == (
        f"/api/v1/products?page=2&ref={REDACTED}&page_size=5")
    assert redact_image_ref("/api/v1/products/abc/assets") == "/api/v1/products/abc/assets"
    assert redact_image_ref("/api/v1/x?preference=valor") == "/api/v1/x?preference=valor"


def test_configure_logging_installs_the_filter_once() -> None:
    configure_logging()
    configure_logging()
    filters = [item for item in logging.getLogger("uvicorn.access").filters if isinstance(item, ImageRefRedactionFilter)]
    assert len(filters) == 1
