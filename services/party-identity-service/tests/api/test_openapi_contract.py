"""OpenAPI coherente con `contracts/rest-api.md` (puerta de calidad 5, RC-09, FR-044)."""

import re
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "party_identity_service"

CONTRACT_OPERATIONS = {
    ("GET", "/api/v1/identification-type-rules"),
    ("POST", "/api/v1/identification-type-rules"),
    ("GET", "/api/v1/identification-type-rules/{rule_id}"),
    ("PUT", "/api/v1/identification-type-rules/{rule_id}"),
    ("POST", "/api/v1/identification-type-rules/{rule_id}/versions"),
    ("POST", "/api/v1/identification-type-rules/{rule_id}/deactivate"),
    ("GET", "/api/v1/person-identities"),
    ("POST", "/api/v1/person-identities"),
    ("GET", "/api/v1/person-identities/{person_identity_id}"),
    ("PUT", "/api/v1/person-identities/{person_identity_id}"),
    ("POST", "/api/v1/person-identities/{person_identity_id}/deactivate"),
    ("POST", "/api/v1/person-identities/{person_identity_id}/reactivate"),
    ("GET", "/api/v1/organization-identities"),
    ("POST", "/api/v1/organization-identities"),
    ("GET", "/api/v1/organization-identities/{organization_identity_id}"),
    ("PUT", "/api/v1/organization-identities/{organization_identity_id}"),
    ("POST", "/api/v1/organization-identities/{organization_identity_id}/deactivate"),
    ("POST", "/api/v1/organization-identities/{organization_identity_id}/reactivate"),
}
HEALTH_OPERATIONS = {
    ("GET", "/health/live"),
    ("GET", "/health/ready"),
}


def _operations(openapi: dict) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, item in openapi["paths"].items()
        for method in item
    }


def test_openapi_matches_contract_exactly(anonymous) -> None:
    operations = _operations(anonymous.get("/openapi.json").json())

    assert operations == CONTRACT_OPERATIONS | HEALTH_OPERATIONS


def test_functional_routes_are_versioned(anonymous) -> None:
    for _, path in _operations(anonymous.get("/openapi.json").json()):
        assert path.startswith("/api/v1/") or path.startswith("/health/"), path


def test_there_is_no_delete_operation(anonymous) -> None:
    assert not any(method == "DELETE" for method, _ in _operations(anonymous.get("/openapi.json").json()))


def test_production_code_has_no_environment_modes_or_test_doubles() -> None:
    """FR-044: un único camino productivo hacia Geography, sin modos por entorno."""
    forbidden = [
        re.compile(r"GEOGRAPHY_MODE"),
        re.compile(r"\bstub\b", re.IGNORECASE),
        re.compile(r"\bFake[A-Z]\w*"),
        re.compile(r"os\.(?:getenv|environ)\(\s*['\"](?:ENV|ENVIRONMENT|APP_ENV)['\"]"),
    ]
    problems = []

    for path in PACKAGE_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden:
            if pattern.search(text):
                problems.append(f"{path.relative_to(PACKAGE_ROOT)}: {pattern.pattern}")

    assert not problems, problems
