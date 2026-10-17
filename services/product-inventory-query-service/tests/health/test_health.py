"""Salud y documentación (FR-022-78, Principio V; T008)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from product_inventory_query_service.main import create_app
from tests.conftest import build_test_settings


def test_live_is_public_and_has_no_dependencies(as_token) -> None:
    response = as_token(None).get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_is_public_without_internal_details(as_token) -> None:
    response = as_token(None).get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_reports_not_ready_without_jwks(as_token, jwks_state) -> None:
    jwks_state["available"] = False
    response = as_token(None).get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_ready_does_not_depend_on_class_c_services(test_auth) -> None:
    """Las URL de CR, PC, Inventory y OC apuntan a hosts inexistentes: `ready` no las consulta."""
    settings = build_test_settings(
        operational_context_base_url="http://127.0.0.1:9/api/v1",
        commercial_relationship_base_url="http://127.0.0.1:9/api/v1",
        product_catalog_base_url="http://127.0.0.1:9/api/v1",
        inventory_base_url="http://127.0.0.1:9/api/v1",
    )
    with TestClient(create_app(settings, auth=test_auth, jwks_probe=lambda: True)) as client:
        assert client.get("/health/ready").status_code == 200
        assert client.get("/health/live").status_code == 200


def test_any_other_route_requires_token(as_token) -> None:
    for path in ("/api/v1/companies/x/product-overviews", "/health/live/x", "/health", "/"):
        response = as_token(None).get(path)
        assert response.status_code == 401, path
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["code"] == "PRODUCT_INVENTORY_QUERY.UNAUTHENTICATED"


def test_docs_only_when_enabled(test_auth) -> None:
    with TestClient(create_app(build_test_settings(docs_enabled=True), auth=test_auth, jwks_probe=lambda: True)) as client:
        assert client.get("/openapi.json").status_code == 200
        assert client.get("/docs").status_code == 200

    with TestClient(create_app(build_test_settings(docs_enabled=False), auth=test_auth, jwks_probe=lambda: True)) as client:
        assert client.get("/openapi.json").status_code in (401, 404)
        assert client.get("/docs").status_code in (401, 404)


def test_trace_id_header_on_every_response(as_token) -> None:
    trace = "4bf92f3577b34da6a3ce929d0e0e4736"
    response = as_token(None).get("/health/live", headers={"traceparent": f"00-{trace}-00f067aa0ba902b7-01"})
    assert response.headers["x-trace-id"] == trace
