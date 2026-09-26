"""Modificación de sucursales (US5; FR-022, FR-025, DS-06, DS-10; pruebas obligatorias 7 y 10)."""

from tests.conftest import update_body


def _url(branch):
    return f"/api/v1/branches/{branch['id']}"


def test_update_version_and_audit(api_as, create_company, create_branch, make_member):
    company = create_company()
    branch = create_branch(company["id"])
    make_member(company["id"], "editor")
    client = api_as("perm:operational-context:branches:update", sub="editor")

    response = client.put(_url(branch), json=update_body(branch, name="Nuevo nombre"))

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2 and body["name"] == "Nuevo nombre"
    assert body["updated_by"] == "editor" and body["created_by"] == branch["created_by"]


def test_stale_version_is_409(api, create_company, create_branch):
    branch = create_branch(create_company()["id"])
    api.put(_url(branch), json=update_body(branch, name="A"))

    response = api.put(_url(branch), json=update_body(branch, name="B"))

    assert response.status_code == 409


def test_identical_put_does_not_write(api, create_company, create_branch, fake_geography, geo):
    branch = create_branch(create_company()["id"], **geo.medellin_location())
    fake_geography.reset()

    response = api.put(_url(branch), json=update_body(branch, code=" med-01 "))

    assert response.status_code == 200
    assert response.json() == branch
    assert fake_geography.count() == 0


def test_company_id_is_immutable(api, create_company, create_branch):
    branch = create_branch(create_company()["id"])
    other = create_company()

    response = api.put(_url(branch), json=update_body(branch, company_id=other["id"]))

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "company_id"


def test_code_change_and_duplicate(api, create_company, create_branch):
    company = create_company()
    first = create_branch(company["id"], code="A-1")
    create_branch(company["id"], code="B-1")

    renamed = api.put(_url(first), json=update_body(first, code="c-1"))
    duplicated = api.put(_url(first), json=update_body(renamed.json(), code="B-1"))

    assert renamed.status_code == 200 and renamed.json()["code"] == "C-1"
    assert renamed.json()["id"] == first["id"]  # DS-10: la referencia es el UUID
    assert duplicated.status_code == 409
    assert duplicated.json()["code"] == "OPERATIONAL_CONTEXT.DUPLICATE_BRANCH_CODE"


def test_no_revalidation_when_location_does_not_change(api, create_company, create_branch, fake_geography, fake_organizations, geo):
    """Prueba obligatoria 7."""
    branch = create_branch(create_company()["id"], **geo.medellin_location())
    fake_geography.reset()
    fake_organizations.reset()
    fake_geography.mode = "unavailable"
    fake_organizations.mode = "unavailable"

    response = api.put(_url(branch), json=update_body(branch, name="Otro", latitude="6.1", longitude="-75.1"))

    assert response.status_code == 200
    assert fake_geography.count() == 0 and fake_organizations.count() == 0


def test_location_change_revalidates_without_party_identity(api, create_company, create_branch, fake_geography, fake_organizations, geo):
    branch = create_branch(create_company()["id"], **geo.medellin_location())
    fake_geography.reset()
    fake_organizations.reset()

    response = api.put(_url(branch), json=update_body(branch, **geo.bogota_location()))

    assert response.status_code == 200
    assert fake_geography.count() == 3
    assert fake_organizations.count() == 0


def test_setting_timezone_to_null_inherits_company(api, create_company, create_branch):
    """Prueba obligatoria 10 (vía PUT)."""
    company = create_company(timezone="America/Lima")
    branch = create_branch(company["id"], timezone="Europe/Madrid")

    response = api.put(_url(branch), json=update_body(branch, timezone=None))

    assert response.status_code == 200
    assert response.json()["timezone"] is None
    assert response.json()["effective_timezone"] == "America/Lima"
