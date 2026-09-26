"""Consulta de empresas (US2; FR-006, FR-015, FR-054)."""

from tests.conftest import random_uuid


def test_get_by_id(api, create_company):
    company = create_company()

    response = api.get(f"/api/v1/companies/{company['id']}")

    assert response.status_code == 200
    assert response.json() == company


def test_get_unknown_is_404(api):
    response = api.get(f"/api/v1/companies/{random_uuid()}")

    assert response.status_code == 404
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.NOT_FOUND"


def test_get_malformed_uuid_is_422(api):
    assert api.get("/api/v1/companies/123").status_code == 422


def test_collection_format_and_pagination(api, create_company):
    for _ in range(3):
        create_company()

    response = api.get("/api/v1/companies", params={"page": 2, "page_size": 2})

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "page", "page_size", "total_records", "total_pages"}
    assert body["page"] == 2 and body["page_size"] == 2
    assert body["total_records"] == 3 and body["total_pages"] == 2
    assert len(body["items"]) == 1


def test_collection_order_is_stable(api, create_company):
    ids = [create_company()["id"] for _ in range(3)]

    body = api.get("/api/v1/companies").json()

    assert [item["id"] for item in body["items"]] == ids


def test_default_status_filter_is_active(api, create_company):
    active = create_company()
    inactive = create_company()
    api.post(f"/api/v1/companies/{inactive['id']}/deactivate", json={"version": 1})

    default = api.get("/api/v1/companies").json()["items"]
    only_inactive = api.get("/api/v1/companies", params={"status": "INACTIVE"}).json()["items"]

    assert [item["id"] for item in default] == [active["id"]]
    assert [item["id"] for item in only_inactive] == [inactive["id"]]


def test_filters(api, create_company, geo):
    in_medellin = create_company(**geo.medellin_location())
    in_bogota = create_company(**geo.bogota_location())
    create_company()

    by_org = api.get("/api/v1/companies", params={"organization_identity_id": in_medellin["organization_identity_id"]})
    by_country = api.get("/api/v1/companies", params={"country_id": str(geo.colombia)})
    by_city = api.get("/api/v1/companies", params={"city_id": str(geo.bogota)})

    assert [i["id"] for i in by_org.json()["items"]] == [in_medellin["id"]]
    assert {i["id"] for i in by_country.json()["items"]} == {in_medellin["id"], in_bogota["id"]}
    assert [i["id"] for i in by_city.json()["items"]] == [in_bogota["id"]]


def test_invalid_status_filter_is_422(api):
    assert api.get("/api/v1/companies", params={"status": "FOO"}).status_code == 422


def test_invalid_pagination_is_422(api):
    assert api.get("/api/v1/companies", params={"page_size": 101}).status_code == 422
    assert api.get("/api/v1/companies", params={"page": 0}).status_code == 422


def test_no_text_search_by_name(api, create_company):
    """DS-13, FR-054: la búsqueda por nombre se hace en Party Identity."""
    create_company()

    response = api.get("/api/v1/companies", params={"search": "algo"})

    assert response.status_code == 200
    assert response.json()["total_records"] == 1  # el parámetro no existe y se ignora
    parameters = {
        parameter["name"]
        for parameter in api.get("/openapi.json").json()["paths"]["/api/v1/companies"]["get"]["parameters"]
    }
    assert "search" not in parameters
