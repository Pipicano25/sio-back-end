"""Formato de errores RFC 9457 y regla 400/422 (FR-001, FR-002, FR-012, R-06)."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

PROBLEM_KEYS = {"type", "title", "status", "detail", "instance", "code", "trace_id"}

UNIT = {
    "code": "KG",
    "name": "Kilogramo",
    "symbol": "kg",
    "measurement_type": "MASS",
    "allows_decimals": True,
}


def _assert_problem(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert PROBLEM_KEYS <= set(body)
    assert body["code"] == f"PRODUCT_CATALOG.{code}"
    assert body["status"] == status
    return body


def test_malformed_json_returns_400(api) -> None:
    response = api.post(
        "/api/v1/units-of-measure",
        content=b"{not json",
        headers={"Content-Type": "application/json"},
    )
    _assert_problem(response, 400, "MALFORMED_REQUEST")


def test_invalid_query_parameter_returns_400(api) -> None:
    response = api.get("/api/v1/units-of-measure?page=abc")
    _assert_problem(response, 400, "MALFORMED_REQUEST")


def test_invalid_field_returns_422_with_field_errors(api) -> None:
    response = api.post("/api/v1/units-of-measure", json={**UNIT, "measurement_type": "TIME"})
    body = _assert_problem(response, 422, "VALIDATION_ERROR")
    assert any(error["field"] == "measurement_type" for error in body["errors"])


def test_company_data_is_rejected(api) -> None:
    for extra in ({"company_id": "x"}, {"sale_price": 10}):
        response = api.post("/api/v1/units-of-measure", json={**UNIT, **extra})
        _assert_problem(response, 422, "VALIDATION_ERROR")


def test_client_cannot_choose_id(api) -> None:
    response = api.post(
        "/api/v1/units-of-measure",
        json={**UNIT, "id": "5f0c6c3e-7a8f-4a44-9d0b-1f2b3c4d5e6f"},
    )
    _assert_problem(response, 422, "VALIDATION_ERROR")


def test_not_found_is_problem(api) -> None:
    response = api.get("/api/v1/units-of-measure/5f0c6c3e-7a8f-4a44-9d0b-1f2b3c4d5e6f")
    _assert_problem(response, 404, "NOT_FOUND")


def test_unauthenticated_is_problem(anonymous) -> None:
    response = anonymous.get("/api/v1/units-of-measure")
    _assert_problem(response, 401, "UNAUTHENTICATED")


def test_forbidden_is_problem(api_as) -> None:
    response = api_as("brands:read").get("/api/v1/units-of-measure")
    _assert_problem(response, 403, "FORBIDDEN")


def test_unexpected_error_hides_internals(app: FastAPI, make_token) -> None:
    @app.get("/api/v1/_boom")
    def boom():
        raise RuntimeError("SELECT secret FROM internal")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/api/v1/_boom",
            headers={"Authorization": f"Bearer {make_token('perm:product-catalog:all:all')}"},
        )

    body = _assert_problem(response, 500, "INTERNAL_ERROR")
    assert "SELECT" not in response.text
    assert body["trace_id"]


def test_method_not_allowed_is_problem(api) -> None:
    response = api.request("PATCH", "/api/v1/units-of-measure")
    _assert_problem(response, 405, "METHOD_NOT_ALLOWED")


def test_generic_framework_errors_use_catalogued_codes(app, make_token) -> None:
    from fastapi import HTTPException

    @app.get("/api/v1/_conflict")
    def conflict():
        raise HTTPException(status_code=409, detail="Conflicto genérico")

    @app.get("/api/v1/_teapot")
    def teapot():
        raise HTTPException(status_code=418, detail="Otro estado")

    headers = {"Authorization": f"Bearer {make_token('perm:product-catalog:all:all')}"}
    with TestClient(app) as client:
        conflict_response = client.get("/api/v1/_conflict", headers=headers)
        other_response = client.get("/api/v1/_teapot", headers=headers)

    _assert_problem(conflict_response, 409, "CONFLICT")
    _assert_problem(other_response, 418, "HTTP_ERROR")


def test_emitted_codes_are_in_catalog() -> None:
    """Todo código que emite `api/errors.py` está en el catálogo cerrado de `contracts/errors.md`."""
    import re
    from pathlib import Path

    from product_catalog_service.api import errors
    from product_catalog_service.application import exceptions

    catalog = Path(__file__).resolve().parents[4] / "specs/002-product-catalog-service/contracts/errors.md"
    documented = set(re.findall(r"^\| `([A-Z_]+)`", catalog.read_text(encoding="utf-8"), flags=re.M))
    spec024 = catalog.parents[2] / "024-product-image-upload/contracts/errors.md"  # códigos de la spec 024
    documented |= set(re.findall(r"^\| `([A-Z_]+)`", spec024.read_text(encoding="utf-8"), flags=re.M))
    documented |= {"CODE_USED_BY_PACKAGING_TYPE", "CODE_USED_BY_UNIT_OF_MEASURE"}

    emitted = {code for code, _ in errors._HTTP_CODES.values()} | {"HTTP_ERROR", "VALIDATION_ERROR", "IMMUTABLE_FIELD", "INTERNAL_ERROR"}
    emitted |= {
        cls.code
        for cls in vars(exceptions).values()
        if isinstance(cls, type) and issubclass(cls, exceptions.DomainError) and cls is not exceptions.DomainError
    }

    assert emitted - documented == set()
