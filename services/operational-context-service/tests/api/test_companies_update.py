"""Modificación de empresas (US5; FR-016, FR-035, FR-063, DS-06, RC-06, RC-10; prueba obligatoria 7)."""

from tests.conftest import random_uuid, update_body


def _url(company):
    return f"/api/v1/companies/{company['id']}"


def test_update_increments_version_and_audit(api_as, create_company, make_member):
    company = create_company()
    make_member(company["id"], "editor")
    client = api_as("perm:operational-context:companies:update", sub="editor")

    response = client.put(_url(company), json=update_body(company, phone="+57 1 111 1111"))

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2
    assert body["phone"] == "+57 1 111 1111"
    assert body["updated_by"] == "editor"
    assert body["created_by"] == company["created_by"]
    assert body["updated_at"] > company["updated_at"]


def test_stale_version_is_409_without_changes(api, create_company):
    company = create_company()
    api.put(_url(company), json=update_body(company, phone="1"))

    response = api.put(_url(company), json=update_body(company, phone="2"))

    assert response.status_code == 409
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.VERSION_CONFLICT"
    assert api.get(_url(company)).json()["phone"] == "1"


def test_identical_put_does_not_write(api, create_company, fake_organizations, fake_geography):
    company = create_company()
    fake_organizations.reset()
    fake_geography.reset()

    response = api.put(_url(company), json=update_body(company, default_currency="cop", phone=f"  {company['phone']} "))

    assert response.status_code == 200
    assert response.json() == company
    assert fake_organizations.count() == 0 and fake_geography.count() == 0


def test_identical_put_with_stale_version_is_409(api, create_company):
    company = create_company()
    api.put(_url(company), json=update_body(company, phone="1"))

    response = api.put(_url(company), json=update_body(company, phone="1"))

    assert response.status_code == 409


def test_null_organization_is_422(api, create_company):
    company = create_company()

    response = api.put(_url(company), json=update_body(company, organization_identity_id=None))

    assert response.status_code == 422


def test_change_organization_validations(api, create_company, fake_organizations):
    company = create_company()
    other = create_company()

    unknown = api.put(_url(company), json=update_body(company, organization_identity_id=random_uuid()))
    inactive = api.put(
        _url(company),
        json=update_body(company, organization_identity_id=str(fake_organizations.add("INACTIVE"))),
    )
    duplicated = api.put(_url(company), json=update_body(company, organization_identity_id=other["organization_identity_id"]))

    assert unknown.status_code == 422
    assert unknown.json()["code"] == "OPERATIONAL_CONTEXT.ORGANIZATION_IDENTITY_NOT_FOUND"
    assert inactive.status_code == 422
    assert inactive.json()["code"] == "OPERATIONAL_CONTEXT.ORGANIZATION_IDENTITY_INACTIVE"
    assert duplicated.status_code == 409


def test_change_organization_calls_party_identity_once_and_not_geography(
    api, create_company, fake_organizations, fake_geography, geo
):
    company = create_company(**geo.medellin_location())
    fake_organizations.reset()
    fake_geography.reset()
    new_organization = fake_organizations.add()

    response = api.put(_url(company), json=update_body(company, organization_identity_id=str(new_organization)))

    assert response.status_code == 200
    assert fake_organizations.count("get_organization") == 1
    assert fake_geography.count() == 0


def test_no_revalidation_when_references_do_not_change(api, create_company, fake_organizations, fake_geography, geo):
    """Prueba obligatoria 7: proveedores caídos y aun así 200 si no cambian las referencias."""
    company = create_company(**geo.medellin_location())
    fake_organizations.reset()
    fake_geography.reset()
    fake_organizations.mode = "unavailable"
    fake_geography.mode = "unavailable"

    response = api.put(_url(company), json=update_body(company, email="nuevo@empresa-ficticia.co"))

    assert response.status_code == 200
    assert fake_organizations.count() == 0 and fake_geography.count() == 0


def test_address_postal_code_and_coordinates_do_not_call_geography(api, create_company, fake_geography, geo):
    company = create_company(**geo.medellin_location())
    fake_geography.reset()

    response = api.put(
        _url(company),
        json=update_body(company, address_line="Otra 2", postal_code="050021", latitude="6.2", longitude="-75.5"),
    )

    assert response.status_code == 200
    assert fake_geography.count() == 0


def test_location_change_revalidates(api, create_company, fake_geography, geo):
    company = create_company(**geo.medellin_location())
    fake_geography.reset()

    response = api.put(_url(company), json=update_body(company, **geo.bogota_location()))

    assert response.status_code == 200
    assert fake_geography.count() == 3


def test_update_with_unknown_field_is_422(api, create_company):
    company = create_company()

    assert api.put(_url(company), json=update_body(company, legal_name="X")).status_code == 422


def test_update_unknown_company_is_404(api, create_company):
    company = create_company()

    assert api.put(f"/api/v1/companies/{random_uuid()}", json=update_body(company)).status_code == 404
