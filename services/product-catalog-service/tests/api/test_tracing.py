"""Trazabilidad `trace_id` (R-07)."""

import re

TRACE_ID = "4bf92f3577b34da6a3ce929d0e0e4736"


def test_traceparent_is_reused(api) -> None:
    response = api.get(
        "/api/v1/units-of-measure",
        headers={"traceparent": f"00-{TRACE_ID}-00f067aa0ba902b7-01"},
    )
    assert response.headers["x-trace-id"] == TRACE_ID


def test_trace_id_is_generated_and_returned_in_errors(api) -> None:
    response = api.get("/api/v1/units-of-measure/5f0c6c3e-7a8f-4a44-9d0b-1f2b3c4d5e6f")
    trace_id = response.headers["x-trace-id"]
    assert re.fullmatch(r"[0-9a-f]{32}", trace_id)
    assert response.json()["trace_id"] == trace_id


def test_invalid_traceparent_is_ignored(api) -> None:
    response = api.get("/api/v1/units-of-measure", headers={"traceparent": "invalid"})
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-trace-id"])


def test_unauthenticated_response_has_trace_id(anonymous) -> None:
    response = anonymous.get("/api/v1/units-of-measure")
    assert response.status_code == 401
    assert response.json()["trace_id"] == response.headers["x-trace-id"]


def test_service_logs_include_trace_id(app, make_token, caplog) -> None:
    """D3: el `trace_id` de la solicitud queda en los registros del servicio."""
    import logging

    from fastapi.testclient import TestClient

    @app.get("/api/v1/_log")
    def emit_logs():
        logging.getLogger("product_catalog_service").warning("registro del servicio")
        logging.getLogger("uvicorn.access").info("registro de acceso")
        return {"ok": True}

    caplog.set_level(logging.INFO)
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/_log",
            headers={
                "Authorization": f"Bearer {make_token('perm:product-catalog:all:all')}",
                "traceparent": f"00-{TRACE_ID}-00f067aa0ba902b7-01",
            },
        )

    assert response.status_code == 200
    records = {
        record.name: record
        for record in caplog.records
        if record.getMessage() in {"registro del servicio", "registro de acceso"}
    }
    assert records["product_catalog_service"].trace_id == TRACE_ID
    assert records["uvicorn.access"].trace_id == TRACE_ID


def test_unexpected_error_log_has_trace_id(app, make_token, caplog) -> None:
    import logging

    from fastapi.testclient import TestClient

    @app.get("/api/v1/_boom_log")
    def boom():
        raise RuntimeError("falla")

    caplog.set_level(logging.ERROR)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/_boom_log",
            headers={"Authorization": f"Bearer {make_token('perm:product-catalog:all:all')}"},
        )

    trace_id = response.headers["x-trace-id"]
    errors = [record for record in caplog.records if record.name == "product_catalog_service"]
    assert errors and all(record.trace_id == trace_id for record in errors)


def test_logging_format_includes_trace_id(app) -> None:
    import logging

    from product_catalog_service.api.tracing import LOG_FORMAT, TraceIdFilter

    for name in ("product_catalog_service", "uvicorn.access"):
        logger = logging.getLogger(name)
        assert sum(isinstance(item, TraceIdFilter) for item in logger.filters) == 1
        for handler in logger.handlers:
            assert handler.formatter._fmt == LOG_FORMAT
    assert "trace_id=%(trace_id)s" in LOG_FORMAT


def test_records_outside_requests_use_placeholder() -> None:
    import logging

    from product_catalog_service.api.tracing import NO_TRACE, TraceIdFilter

    record = logging.LogRecord("x", logging.INFO, __file__, 1, "sin solicitud", None, None)
    TraceIdFilter().filter(record)
    assert record.trace_id == NO_TRACE
