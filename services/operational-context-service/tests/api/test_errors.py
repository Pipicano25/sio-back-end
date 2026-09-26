"""Problem Details RFC 9457 y trazabilidad (FR-004, FR-005, Principio XII, D3, D14)."""

import inspect
import pkgutil

import pytest

import operational_context_service.application as application_package
import operational_context_service.domain as domain_package
from operational_context_service.api.errors import _STATUS_BY_CODE
from operational_context_service.application import exceptions as app_exceptions
from operational_context_service.domain.errors import OperationalContextError

PROBLEM_KEYS = {"type", "title", "status", "detail", "instance", "code", "trace_id"}
TRACEPARENT = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"


def test_not_found_is_problem_details(api):
    response = api.get("/api/v1/companies/00000000-0000-4000-8000-000000000001")

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert PROBLEM_KEYS <= set(body)
    assert body["code"] == "OPERATIONAL_CONTEXT.NOT_FOUND"
    assert body["type"] == "https://sio/errors/operational-context/not-found"
    assert body["instance"] == "/api/v1/companies/00000000-0000-4000-8000-000000000001"
    assert body["trace_id"] == response.headers["x-trace-id"]


def test_trace_id_taken_from_valid_traceparent(api):
    response = api.get(
        "/api/v1/companies/00000000-0000-4000-8000-000000000001",
        headers={"traceparent": TRACEPARENT},
    )

    assert response.headers["x-trace-id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert response.json()["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"


@pytest.mark.parametrize("traceparent", [None, "invalido", "00-" + "0" * 32 + "-00f067aa0ba902b7-01"])
def test_trace_id_generated_when_missing_or_invalid(api, traceparent):
    headers = {"traceparent": traceparent} if traceparent else {}
    response = api.get("/api/v1/companies", headers=headers)

    assert response.status_code == 200
    trace_id = response.headers["x-trace-id"]
    assert len(trace_id) == 32 and trace_id != "0" * 32


def test_trace_id_on_success(api):
    response = api.get("/api/v1/companies")

    assert "x-trace-id" in response.headers


def test_malformed_json_is_400(api):
    response = api.post(
        "/api/v1/companies",
        content=b"{no es json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.MALFORMED_REQUEST"


def test_validation_error_is_422_with_field_detail(api):
    response = api.post("/api/v1/companies", json={"organization_identity_id": "no-es-uuid"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.VALIDATION_ERROR"
    assert {"field", "message", "code"} <= set(body["errors"][0])
    assert body["errors"][0]["field"] == "organization_identity_id"


def test_malformed_uuid_in_path_is_422_not_404(api):
    response = api.get("/api/v1/companies/no-es-uuid")

    assert response.status_code == 422


def test_unhandled_error_is_500_without_trace(api, fake_organizations):
    def explode(_):
        raise RuntimeError("detalle interno secreto")

    fake_organizations.get_organization = explode
    response = api.post("/api/v1/companies", json={"organization_identity_id": "00000000-0000-4000-8000-000000000009"})

    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.INTERNAL_ERROR"
    assert "secreto" not in response.text
    assert "Traceback" not in response.text


def _application_error_classes():
    classes = []
    for module in (app_exceptions,):
        for _, value in inspect.getmembers(module, inspect.isclass):
            if issubclass(value, OperationalContextError) and value is not OperationalContextError:
                classes.append(value)
    return classes


@pytest.mark.parametrize("error_class", _application_error_classes(), ids=lambda cls: cls.__name__)
def test_every_application_code_has_http_status(error_class):
    assert error_class.code in _STATUS_BY_CODE


def test_application_and_domain_do_not_define_http_status():
    """Principio XII: el estado HTTP solo se asigna en api/errors.py."""
    for package in (application_package, domain_package):
        for module_info in pkgutil.iter_modules(package.__path__):
            module = __import__(f"{package.__name__}.{module_info.name}", fromlist=["*"])
            source = inspect.getsource(module)
            assert "status_code" not in source, module.__name__
            assert "fastapi" not in source.lower(), module.__name__
            assert "starlette" not in source.lower(), module.__name__


# --------------------------------------------------------------------------
# Fase B: extensión `dependency` en DEPENDENCY_UNAVAILABLE (C-13) y códigos nuevos.
# --------------------------------------------------------------------------


def test_party_identity_unavailable_keeps_code_and_adds_dependency(api, fake_organizations):
    fake_organizations.mode = "unavailable"

    response = api.post(
        "/api/v1/companies",
        json={"organization_identity_id": str(fake_organizations.add())},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "party-identity"


def test_geography_unavailable_keeps_code_and_adds_dependency(api, fake_organizations, fake_geography, geo):
    fake_geography.mode = "unavailable"

    response = api.post(
        "/api/v1/companies",
        json={
            "organization_identity_id": str(fake_organizations.add()),
            "country_id": str(geo.colombia),
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE"
    assert body["dependency"] == "geography"


def test_new_phase_b_codes_have_http_status():
    from operational_context_service.api.errors import status_for_code

    expected = {
        "KEYCLOAK_USER_NOT_FOUND": 422,
        "KEYCLOAK_USER_DISABLED": 422,
        "TECHNICAL_ACCOUNT_NOT_ALLOWED": 422,
        "PERSON_IDENTITY_NOT_FOUND": 422,
        "PERSON_IDENTITY_INACTIVE": 422,
        "MEMBERSHIP_INACTIVE": 422,
        "BRANCH_INACTIVE": 422,
        "BRANCH_COMPANY_MISMATCH": 422,
        "INVALID_VALIDITY_PERIOD": 422,
        "DUPLICATE_MEMBERSHIP": 409,
        "DUPLICATE_USER_BRANCH": 409,
        "PRIMARY_ADVISOR_EXISTS": 409,
        "DUPLICATE_ADVISOR_ASSIGNMENT": 409,
        "NO_ACTIVE_PRIMARY_ADVISOR": 409,
        "PRIMARY_ADVISOR_MISMATCH": 409,
        "DEPENDENCY_UNAVAILABLE": 503,
    }

    assert {code: status_for_code(code) for code in expected} == expected
