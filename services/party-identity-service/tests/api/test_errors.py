"""Pruebas del modelo de errores RFC 9457 y de la trazabilidad (FR-001, FR-005, FR-006)."""

import ast
from pathlib import Path

import pytest
from fastapi import APIRouter

from party_identity_service.api import errors as api_errors
from party_identity_service.application import exceptions as app_exceptions
from tests.conftest import person_payload, random_uuid

PROBLEM_FIELDS = {"type", "title", "status", "detail", "instance", "code", "trace_id"}
PACKAGE_ROOT = Path(app_exceptions.__file__).resolve().parents[1]


def _assert_problem(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert PROBLEM_FIELDS.issubset(body)
    assert body["status"] == status
    assert body["code"] == f"PARTY_IDENTITY.{code}"
    assert body["trace_id"]
    assert response.headers["x-trace-id"] == body["trace_id"]
    return body


def test_not_found_is_problem_details(api) -> None:
    body = _assert_problem(api.get(f"/api/v1/person-identities/{random_uuid()}"), 404, "NOT_FOUND")

    assert body["type"] == "https://sio/errors/party-identity/not-found"
    assert body["instance"].startswith("/api/v1/person-identities/")


def test_success_responses_include_trace_header(api) -> None:
    response = api.get("/api/v1/person-identities")

    assert response.status_code == 200
    assert response.headers["x-trace-id"]


def test_trace_id_is_taken_from_valid_traceparent(api) -> None:
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    response = api.get(
        f"/api/v1/person-identities/{random_uuid()}",
        headers={"traceparent": f"00-{trace_id}-00f067aa0ba902b7-01"},
    )

    assert response.headers["x-trace-id"] == trace_id
    assert response.json()["trace_id"] == trace_id


def test_invalid_json_is_malformed_request(api) -> None:
    response = api.post(
        "/api/v1/person-identities",
        content=b"{no-json",
        headers={"content-type": "application/json"},
    )

    _assert_problem(response, 400, "MALFORMED_REQUEST")


def test_invalid_field_is_validation_error_with_field_detail(api) -> None:
    response = api.post(
        "/api/v1/person-identities",
        json=person_payload(first_name=""),
    )

    body = _assert_problem(response, 422, "VALIDATION_ERROR")
    assert any(error["field"] == "first_name" for error in body["errors"])
    assert all(error["code"] == "VALIDATION_ERROR" for error in body["errors"])


def test_malformed_uuid_in_path_is_validation_error(api) -> None:
    _assert_problem(api.get("/api/v1/person-identities/no-es-uuid"), 422, "VALIDATION_ERROR")


def test_legacy_routes_without_prefix_do_not_exist(api) -> None:
    response = api.get("/person-identities")

    _assert_problem(response, 404, "NOT_FOUND")


def test_unhandled_error_is_internal_error_without_trace(app, api) -> None:
    router = APIRouter()

    @router.get("/api/v1/_boom")
    def boom():
        raise RuntimeError("detalle interno que no debe filtrarse")

    app.include_router(router)
    response = api.get("/api/v1/_boom")

    body = _assert_problem(response, 500, "INTERNAL_ERROR")
    assert "detalle interno" not in response.text
    assert "Traceback" not in body["detail"]


def _application_error_classes() -> list[type]:
    return [
        value
        for value in vars(app_exceptions).values()
        if isinstance(value, type)
        and issubclass(value, app_exceptions.PartyIdentityError)
        and value is not app_exceptions.PartyIdentityError
    ]


@pytest.mark.parametrize("error_class", _application_error_classes(), ids=lambda cls: cls.__name__)
def test_every_application_code_has_http_status(error_class: type) -> None:
    assert api_errors.status_for_code(error_class.code) is not None


def test_application_and_domain_layers_do_not_define_http_status() -> None:
    """Principio XII: solo `api/errors.py` asigna estados HTTP (C2)."""
    forbidden_names = {"status_code", "http_status"}
    forbidden_modules = {"fastapi", "starlette"}

    for layer in ("application", "domain"):
        for path in (PACKAGE_ROOT / layer).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    assert node.id not in forbidden_names, path
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = getattr(node, "module", None) or ""
                    names = [alias.name for alias in node.names]
                    for name in [module, *names]:
                        assert name.split(".")[0] not in forbidden_modules, path
