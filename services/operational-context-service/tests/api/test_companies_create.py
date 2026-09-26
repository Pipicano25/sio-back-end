"""Alta de empresas (US2; FR-010 a FR-014, FR-061, RC-03, RC-10; pruebas obligatorias 1, 2, 3 y 12)."""

import logging

import pytest

from operational_context_service.observability import SERVICE_LOGGER
from tests.conftest import company_payload, random_uuid

URL = "/api/v1/companies"


def _count(test_engine):
    from sqlalchemy import text

    with test_engine.connect() as connection:
        return connection.execute(text("SELECT count(*) FROM companies")).scalar_one()


def test_create_with_defaults(api_as, fake_organizations):
    organization_id = fake_organizations.add()
    client = api_as("perm:operational-context:companies:create", sub="admin-sub")

    response = client.post(URL, json=company_payload(organization_id))

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"/api/v1/companies/{body['id']}"
    assert body["organization_identity_id"] == str(organization_id)
    assert body["status"] == "ACTIVE"
    assert body["timezone"] == "America/Bogota"
    assert body["default_currency"] == "COP"
    assert body["version"] == 1
    assert body["created_by"] == body["updated_by"] == "admin-sub"
    for owned_by_party_identity in ("legal_name", "trade_name", "identification_type", "identification_number"):
        assert owned_by_party_identity not in body
    assert fake_organizations.count("get_organization") == 1


def test_organization_is_required(api):
    response = api.post(URL, json={"email": "a@empresa-ficticia.co"})

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "organization_identity_id"


def test_organization_cannot_be_null(api):
    response = api.post(URL, json={"organization_identity_id": None})

    assert response.status_code == 422


def test_unknown_organization_is_422(api, test_engine, caplog):
    """Prueba obligatoria 1."""
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)
    unknown = random_uuid()

    response = api.post(URL, json=company_payload(unknown))

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.ORGANIZATION_IDENTITY_NOT_FOUND"
    assert body["errors"][0]["field"] == "organization_identity_id"
    assert _count(test_engine) == 0
    records = [r for r in caplog.records if "ORGANIZATION_IDENTITY_NOT_FOUND" in r.getMessage()]
    assert records and records[-1].levelno == logging.INFO
    message = records[-1].getMessage()
    assert unknown in message and "organization_identity_id" in message
    assert records[-1].trace_id == response.headers["x-trace-id"]
    assert "Bearer" not in message and "contacto@" not in message


def test_inactive_organization_is_422(api, fake_organizations, test_engine, caplog):
    """Prueba obligatoria 2 (referencia nueva)."""
    caplog.set_level(logging.INFO, logger=SERVICE_LOGGER)
    organization_id = fake_organizations.add("INACTIVE")

    response = api.post(URL, json=company_payload(organization_id))

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.ORGANIZATION_IDENTITY_INACTIVE"
    assert _count(test_engine) == 0
    records = [r for r in caplog.records if "ORGANIZATION_IDENTITY_INACTIVE" in r.getMessage()]
    assert records and records[-1].levelno == logging.INFO
    assert str(organization_id) in records[-1].getMessage()


def test_party_identity_unavailable_is_503(api, fake_organizations, test_engine):
    """Prueba obligatoria 3."""
    fake_organizations.mode = "unavailable"

    response = api.post(URL, json=company_payload(random_uuid()))

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.DEPENDENCY_UNAVAILABLE"
    assert "PARTY_IDENTITY_UNAVAILABLE" not in response.text
    assert _count(test_engine) == 0


def test_duplicate_organization_is_409_without_calling_party_identity(api, create_company, fake_organizations):
    company = create_company()
    fake_organizations.reset()

    response = api.post(URL, json=company_payload(company["organization_identity_id"]))

    assert response.status_code == 409
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.DUPLICATE_ORGANIZATION_IDENTITY"
    assert fake_organizations.count() == 0


@pytest.mark.parametrize("timezone", ["Bogota", "GMT-5", "America/Nowhere"])
def test_invalid_timezone_is_422(api, fake_organizations, timezone):
    response = api.post(URL, json=company_payload(fake_organizations.add(), timezone=timezone))

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "OPERATIONAL_CONTEXT.VALIDATION_ERROR"
    assert body["errors"][0]["field"] == "timezone"


def test_explicit_timezone_is_kept(api, fake_organizations):
    response = api.post(URL, json=company_payload(fake_organizations.add(), timezone="Europe/Madrid"))

    assert response.status_code == 201
    assert response.json()["timezone"] == "Europe/Madrid"


def test_currency_is_normalized(api, fake_organizations):
    response = api.post(URL, json=company_payload(fake_organizations.add(), default_currency=" usd "))

    assert response.status_code == 201
    assert response.json()["default_currency"] == "USD"


@pytest.mark.parametrize("currency", ["US", "USDD", "U5D"])
def test_invalid_currency_is_422(api, fake_organizations, currency):
    response = api.post(URL, json=company_payload(fake_organizations.add(), default_currency=currency))

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "default_currency"


def test_invalid_email_is_422(api, fake_organizations):
    response = api.post(URL, json=company_payload(fake_organizations.add(), email="no-es-correo"))

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "email"


def test_email_domain_is_lowercased_local_part_kept(api, fake_organizations):
    """C3, R-08: solo el dominio pasa a minúsculas."""
    response = api.post(URL, json=company_payload(fake_organizations.add(), email="Usuario@EJEMPLO.COM"))

    assert response.status_code == 201
    assert response.json()["email"] == "Usuario@ejemplo.com"


def test_blank_optional_strings_become_null(api, fake_organizations):
    response = api.post(URL, json=company_payload(fake_organizations.add(), phone="   ", address_line=""))

    assert response.status_code == 201
    assert response.json()["phone"] is None
    assert response.json()["address_line"] is None


@pytest.mark.parametrize(
    "unknown_field",
    ["created_by", "updated_by", "status", "legal_name", "trade_name", "identification_number", "foo"],
)
def test_unknown_fields_are_422(api, fake_organizations, unknown_field):
    """Prueba obligatoria 12."""
    response = api.post(URL, json=company_payload(fake_organizations.add(), **{unknown_field: "x"}))

    assert response.status_code == 422
    assert response.json()["code"] == "OPERATIONAL_CONTEXT.VALIDATION_ERROR"
    assert response.json()["errors"][0]["field"] == unknown_field
    assert fake_organizations.count() == 0
