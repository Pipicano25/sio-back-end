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


# --------------------------------------------------------------------------
# Fase B: extensión `dependency` y códigos nuevos (T006; RC-19, C-09, FR-003)
# --------------------------------------------------------------------------


def test_phase_a_dependency_unavailable_keeps_code_and_adds_dependency(api, fake_countries) -> None:
    """Regla 4.3: mismo estado y `code` de la Fase A, con `dependency: geography`."""
    fake_countries.mode = "unavailable"

    body = _assert_problem(
        api.post("/api/v1/organization-identities", json={
            "country_id": random_uuid(),
            "identification_type": "NIT",
            "identification_number": "900000001-1",
            "legal_name": "ORGANIZACION FICTICIA S.A.S.",
        }),
        503,
        "DEPENDENCY_UNAVAILABLE",
    )

    assert body["dependency"] == "geography"


@pytest.mark.parametrize("dependency", ["geography", "operational-context", "keycloak"])
def test_dependency_unavailable_problem_carries_dependency(app, api, dependency: str) -> None:
    router = APIRouter()

    @router.get("/api/v1/_dependency")
    def fail():
        raise app_exceptions.DependencyUnavailableError(dependency=dependency, cause="TEST")

    app.include_router(router)
    body = _assert_problem(api.get("/api/v1/_dependency"), 503, "DEPENDENCY_UNAVAILABLE")

    assert body["dependency"] == dependency
    assert "TEST" not in body["detail"]


def test_confirmation_membership_invalid_carries_reason(app, api) -> None:
    router = APIRouter()

    @router.get("/api/v1/_membership")
    def fail():
        raise app_exceptions.ConfirmationMembershipInvalidError(reason="USER_NOT_MEMBER")

    app.include_router(router)
    body = _assert_problem(api.get("/api/v1/_membership"), 422, "CONFIRMATION_MEMBERSHIP_INVALID")

    assert body["reason"] == "USER_NOT_MEMBER"


@pytest.mark.parametrize(
    "error_class, code",
    [
        ("LocationInactiveError", "LOCATION_INACTIVE"),
        ("GeographyIncoherentError", "GEOGRAPHY_INCOHERENT"),
        ("GeographyParentRequiredError", "GEOGRAPHY_PARENT_REQUIRED"),
    ],
)
def test_geography_errors_carry_field(app, api, error_class: str, code: str) -> None:
    router = APIRouter()

    @router.get("/api/v1/_geo")
    def fail():
        raise getattr(app_exceptions, error_class)(field="city_id")

    app.include_router(router)
    body = _assert_problem(api.get("/api/v1/_geo"), 422, code)

    assert body["field"] == "city_id"


PHASE_B_STATUS = {
    "CONTACT_PROFILE_NOT_FOUND": 404,
    "CONTACT_PROFILE_ALREADY_CLOSED": 409,
    "PERSON_IDENTITY_INACTIVE": 422,
    "ORGANIZATION_IDENTITY_INACTIVE": 422,
    "PERSON_IDENTITY_NOT_FOUND": 422,
    "ADMINISTRATIVE_DIVISION_NOT_FOUND": 422,
    "CITY_NOT_FOUND": 422,
    "LOCATION_INACTIVE": 422,
    "GEOGRAPHY_INCOHERENT": 422,
    "GEOGRAPHY_PARENT_REQUIRED": 422,
    "COMPANY_NOT_FOUND": 422,
    "COMPANY_INACTIVE": 422,
    "CONFIRMATION_MEMBERSHIP_INVALID": 422,
    "INVALID_PRIMARY_CONTACT": 422,
    "PRIMARY_CONTACT_CONFLICT": 409,
    "DUPLICATE_ACTIVE_CONTACT_PERSON": 409,
    "DUPLICATE_SECTOR_CODE": 409,
    "INVALID_SECTOR_HIERARCHY": 422,
    "SECTOR_HAS_ACTIVE_CHILDREN": 409,
    "SECTOR_INACTIVE": 422,
    "DUPLICATE_ACTIVE_SECTOR_ASSIGNMENT": 409,
    "PRIMARY_SECTOR_CONFLICT": 409,
    "INVALID_PRIMARY_SECTOR": 422,
    "PRIMARY_REPRESENTATIVE_CONFLICT": 409,
    "DUPLICATE_ACTIVE_REPRESENTATIVE": 409,
}


@pytest.mark.parametrize("code, status", sorted(PHASE_B_STATUS.items()))
def test_phase_b_codes_have_contract_status(code: str, status: int) -> None:
    """Catálogo de `contracts/errors.md` de la feature 006."""
    assert api_errors.status_for_code(code) == status
    assert any(cls.code == code for cls in _application_error_classes())
