"""Problem Details (T006; FR-022-71, FR-022-73, D3)."""

from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.testclient import TestClient

from product_inventory_query_service.api.errors import register_error_handlers
from product_inventory_query_service.api.tracing import TracingMiddleware
from product_inventory_query_service.application.exceptions import (
    DependencyUnavailableError,
    ForbiddenFilterError,
    InvalidCursorError,
    NotFoundError,
)


def _client() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/dependency")
    def dependency() -> None:
        raise DependencyUnavailableError("inventory", "balances_lookup", "timeout")

    @app.get("/cursor/{cause}")
    def cursor(cause: str) -> None:
        raise InvalidCursorError(cause)

    @app.get("/not-found")
    def not_found() -> None:
        raise NotFoundError("La empresa no existe o no tiene acceso.")

    @app.get("/forbidden")
    def forbidden() -> None:
        raise ForbiddenFilterError("No tiene permiso para filtrar por existencias.")

    @app.get("/validation")
    def validation(page_size: int = Query(ge=1, le=20)) -> dict[str, int]:
        return {"page_size": page_size}

    app.add_middleware(TracingMiddleware)
    return TestClient(app, raise_server_exceptions=False)


def test_dependency_unavailable_is_503_without_naming_the_dependency() -> None:
    response = _client().get("/dependency")
    body = response.json()
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert body["code"] == "PRODUCT_INVENTORY_QUERY.DEPENDENCY_UNAVAILABLE"
    assert body["trace_id"]
    assert "dependency" not in body
    assert "balances_lookup" not in response.text and "timeout" not in response.text
    assert "items" not in body


def test_every_invalid_cursor_cause_gets_the_same_response() -> None:
    client = _client()
    bodies = [client.get(f"/cursor/{cause}").json() for cause in ("malformed", "signature", "company", "endpoint")]
    for body in bodies:
        assert body["status"] == 422
        assert body["code"] == "PRODUCT_INVENTORY_QUERY.INVALID_CURSOR"
    assert len({body["detail"] for body in bodies}) == 1
    assert all("company" not in body["detail"] and "signature" not in body["detail"] for body in bodies)


def test_not_found_forbidden_and_validation_codes() -> None:
    client = _client()
    assert client.get("/not-found").json()["code"] == "PRODUCT_INVENTORY_QUERY.NOT_FOUND"
    forbidden = client.get("/forbidden")
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == "PRODUCT_INVENTORY_QUERY.FORBIDDEN"
    invalid = client.get("/validation", params={"page_size": 21})
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "PRODUCT_INVENTORY_QUERY.VALIDATION_ERROR"
    assert invalid.json()["errors"][0]["field"] == "page_size"
