"""El OpenAPI generado coincide con `contracts/rest-api.md` (FR-053, FR-079, puerta de calidad 5)."""

import pytest

EXPECTED_OPERATIONS = {
    ("get", "/api/v1/companies"),
    ("post", "/api/v1/companies"),
    ("get", "/api/v1/companies/{company_id}"),
    ("put", "/api/v1/companies/{company_id}"),
    ("post", "/api/v1/companies/{company_id}/deactivate"),
    ("post", "/api/v1/companies/{company_id}/reactivate"),
    ("get", "/api/v1/companies/{company_id}/branches"),
    ("post", "/api/v1/companies/{company_id}/branches"),
    ("get", "/api/v1/branches/{branch_id}"),
    ("put", "/api/v1/branches/{branch_id}"),
    ("post", "/api/v1/branches/{branch_id}/deactivate"),
    ("post", "/api/v1/branches/{branch_id}/reactivate"),
    ("get", "/health/live"),
    ("get", "/health/ready"),
}

COMPANY_RESPONSE = {
    "id", "organization_identity_id", "email", "phone", "address_line", "country_id",
    "administrative_division_id", "city_id", "postal_code", "latitude", "longitude", "timezone",
    "default_currency", "status", "version", "created_by", "updated_by", "created_at", "updated_at",
}
BRANCH_RESPONSE = {
    "id", "company_id", "company_status", "code", "name", "email", "phone", "address_line",
    "country_id", "administrative_division_id", "city_id", "postal_code", "latitude", "longitude",
    "timezone", "effective_timezone", "status", "version", "created_by", "updated_by", "created_at",
    "updated_at",
}
COMPANY_INPUT = {
    "organization_identity_id", "email", "phone", "address_line", "country_id",
    "administrative_division_id", "city_id", "postal_code", "latitude", "longitude", "timezone",
    "default_currency",
}
BRANCH_INPUT = {
    "code", "name", "email", "phone", "address_line", "country_id", "administrative_division_id",
    "city_id", "postal_code", "latitude", "longitude", "timezone",
}


@pytest.fixture
def spec(anonymous):
    return anonymous.get("/openapi.json").json()


def _schema(spec, name):
    return spec["components"]["schemas"][name]


def test_operations_match_contract(spec):
    operations = {(method, path) for path, item in spec["paths"].items() for method in item}

    assert operations == EXPECTED_OPERATIONS


def test_no_delete_operations(spec):
    assert not any("delete" in item for item in spec["paths"].values())


def test_response_schemas(spec):
    assert set(_schema(spec, "CompanyResponse")["properties"]) == COMPANY_RESPONSE
    assert set(_schema(spec, "BranchResponse")["properties"]) == BRANCH_RESPONSE


def test_input_schemas(spec):
    assert set(_schema(spec, "CompanyCreate")["properties"]) == COMPANY_INPUT
    assert set(_schema(spec, "CompanyUpdate")["properties"]) == COMPANY_INPUT | {"version"}
    assert set(_schema(spec, "BranchCreate")["properties"]) == BRANCH_INPUT
    assert set(_schema(spec, "BranchUpdate")["properties"]) == BRANCH_INPUT | {"version"}
    assert set(_schema(spec, "StatusActionRequest")["properties"]) == {"version"}
    assert set(_schema(spec, "CompanyCreate")["required"]) == {"organization_identity_id"}
    assert set(_schema(spec, "BranchCreate")["required"]) == {"code", "name"}
    for name in ("CompanyCreate", "CompanyUpdate", "BranchCreate", "BranchUpdate", "StatusActionRequest"):
        assert _schema(spec, name).get("additionalProperties") is False, name


def test_collection_parameters(spec):
    def params(path):
        return {p["name"] for p in spec["paths"][path]["get"]["parameters"] if p["in"] == "query"}

    assert params("/api/v1/companies") == {
        "page", "page_size", "status", "organization_identity_id", "country_id", "city_id",
    }
    assert params("/api/v1/companies/{company_id}/branches") == {
        "page", "page_size", "search", "status", "city_id",
    }


def test_functional_routes_require_bearer(spec):
    for path, item in spec["paths"].items():
        for operation in item.values():
            expected = [] if path.startswith("/health") else [{"BearerAuth": []}]
            assert operation["security"] == expected, path


def test_created_status_codes(spec):
    assert "201" in spec["paths"]["/api/v1/companies"]["post"]["responses"]
    assert "201" in spec["paths"]["/api/v1/companies/{company_id}/branches"]["post"]["responses"]
