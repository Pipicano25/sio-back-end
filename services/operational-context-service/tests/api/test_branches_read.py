"""Consulta de sucursales (US4; FR-023, FR-024, R-10; pruebas obligatorias 10 y 11)."""

from sqlalchemy import text

from tests.conftest import random_uuid, update_body


def test_get_includes_calculated_fields(api, create_company, create_branch):
    company = create_company()
    branch = create_branch(company["id"])

    response = api.get(f"/api/v1/branches/{branch['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body == branch
    assert body["company_id"] == company["id"]
    assert body["company_status"] == "ACTIVE"


def test_null_timezone_uses_company_timezone(api, create_company, create_branch, test_engine):
    """Prueba obligatoria 10: hereda sin copiar, y sigue a la empresa si esta cambia."""
    company = create_company(timezone="America/Lima")
    branch = create_branch(company["id"])

    assert branch["timezone"] is None
    assert branch["effective_timezone"] == "America/Lima"

    api.put(
        f"/api/v1/companies/{company['id']}",
        json=update_body(company, timezone="Europe/Madrid"),
    )
    reloaded = api.get(f"/api/v1/branches/{branch['id']}").json()

    assert reloaded["effective_timezone"] == "Europe/Madrid"
    assert reloaded["version"] == branch["version"]
    with test_engine.connect() as connection:
        stored = connection.execute(
            text("SELECT timezone FROM branches WHERE id = :id"), {"id": branch["id"]}
        ).scalar_one()
    assert stored is None  # DS-08: la zona de la empresa nunca se copia


def test_own_timezone_prevails(api, create_company, create_branch):
    """Prueba obligatoria 11."""
    company = create_company(timezone="America/Bogota")
    branch = create_branch(company["id"], timezone="America/Lima")

    assert branch["timezone"] == "America/Lima"
    assert branch["effective_timezone"] == "America/Lima"
    assert api.get(f"/api/v1/branches/{branch['id']}").json()["effective_timezone"] == "America/Lima"


def test_get_unknown_is_404_and_malformed_is_422(api):
    assert api.get(f"/api/v1/branches/{random_uuid()}").status_code == 404
    assert api.get("/api/v1/branches/xyz").status_code == 422


def test_collection_defaults_filters_and_search(api, create_company, create_branch, geo):
    company = create_company()
    other = create_company()
    medellin = create_branch(company["id"], code="MED-01", name="Tienda Poblado", **geo.medellin_location())
    bogota = create_branch(company["id"], code="BOG-01", name="Bodega Norte", **geo.bogota_location())
    closed = create_branch(company["id"], code="CAL-01", name="Tienda Cerrada")
    create_branch(other["id"], code="MED-01", name="Otra empresa")
    api.post(f"/api/v1/branches/{closed['id']}/deactivate", json={"version": 1})
    url = f"/api/v1/companies/{company['id']}/branches"

    default = api.get(url).json()
    inactive = api.get(url, params={"status": "INACTIVE"}).json()
    by_city = api.get(url, params={"city_id": str(geo.bogota)}).json()
    by_search = api.get(url, params={"search": "tienda"}).json()
    by_code = api.get(url, params={"search": "bog"}).json()

    assert [i["id"] for i in default["items"]] == [medellin["id"], bogota["id"]]
    assert default["total_records"] == 2 and default["total_pages"] == 1
    assert [i["id"] for i in inactive["items"]] == [closed["id"]]
    assert [i["id"] for i in by_city["items"]] == [bogota["id"]]
    assert [i["id"] for i in by_search["items"]] == [medellin["id"]]
    assert [i["id"] for i in by_code["items"]] == [bogota["id"]]


def test_collection_of_unknown_company_is_404(api):
    response = api.get(f"/api/v1/companies/{random_uuid()}/branches")

    assert response.status_code == 404


def test_collection_invalid_status_is_422(api, create_company):
    company = create_company()

    assert api.get(f"/api/v1/companies/{company['id']}/branches", params={"status": "X"}).status_code == 422
