"""Fabricante por la vista de contrato de Party Identity frente al adaptador HTTP (spec 025, T071).

Crea en el contenedor de pruebas de Product Catalog la base ``product_catalog_test__pi`` con las migraciones reales de
Party Identity y el rol ``pc_contract_reader`` con su ``contract/grants.yaml`` (una sola contraseña por ejecución: los
roles son del servidor), y comprueba:

- ``ContractPartyIdentityManufacturerDirectory.exists`` devuelve lo mismo que ``HTTPPartyIdentityManufacturerDirectory``
  cuando Party Identity responde lo que respondería con esos datos (``200`` para organizaciones activas e inactivas,
  ``404`` si no existe);
- sin token o sin ``perm:party-identity:organization_identities:read`` → la misma
  ``ManufacturerDirectoryAccessDeniedError`` que hoy producen el ``401``/``403`` (FR-037);
- base detenida → la misma ``ManufacturerDirectoryUnavailableError`` que hoy produce un error de red o un ``5xx``;
- ``POST /products`` con ``PARTY_IDENTITY_READ_SOURCE=contract`` responde lo mismo que con HTTP (creado, ``422``
  ``MANUFACTURER_NOT_FOUND``, ``403`` ``MANUFACTURER_ACCESS_DENIED`` y ``503``) sin ninguna solicitud a Party Identity.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sio_auth import TokenClaims
from sio_auth.permissions import extract_permission_grants
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sqlalchemy import create_engine, text

from product_catalog_service.application.exceptions import (
    ManufacturerDirectoryAccessDeniedError,
    ManufacturerDirectoryUnavailableError,
)
from product_catalog_service.config import Settings
from product_catalog_service.infrastructure.contract_party_identity import ContractPartyIdentityManufacturerDirectory
from product_catalog_service.infrastructure.party_identity_manufacturer_directory import (
    HTTPPartyIdentityManufacturerDirectory,
)
from product_catalog_service.main import create_app
from tests import factories
from tests.conftest import ApiClient

SERVICES = Path(__file__).resolve().parents[3]
OWNER = SERVICES / "party-identity-service"
OWNER_ENV = {"PARTY_IDENTITY_SEED_COUNTRY_ID": "6f1c1b54-0d0e-4a63-9a8c-6f0f8f7f1a11"}
CONSUMER = "product-catalog"
ORGANIZATIONS_READ = "perm:party-identity:organization_identities:read"
WHO = "prueba-spec-025"


# --------------------------------------------------------------------------- infraestructura


@pytest.fixture(scope="module")
def owner(test_database_url):
    url = create_owner_schema(test_database_url, "product_catalog_test__pi", OWNER, OWNER_ENV, recreate=True)
    reader_url = provision_reader(url, OWNER / "contract" / "grants.yaml", CONSUMER, secrets.token_urlsafe(24))
    settings = ContractReadSettings(prefix="PARTY_IDENTITY", source="contract", database_url=reader_url,
                                    timeout_seconds=2)
    admin = create_engine(url)
    reader = create_contract_engine(settings, application_name="pc-t071")
    yield {"admin": admin, "reader": reader, "settings": settings}
    admin.dispose()
    reader.dispose()


def down_settings() -> ContractReadSettings:
    return ContractReadSettings(
        prefix="PARTY_IDENTITY", source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url="postgresql+psycopg://pc_contract_reader:x@127.0.0.1:1/product_catalog_test__pi",
    )


def claims(*roles: str) -> TokenClaims:
    return TokenClaims(
        subject="user-admin", issuer="test", audiences=("sio-api",),
        expires_at=datetime.now(UTC) + timedelta(minutes=5), roles=frozenset(roles),
        permissions=extract_permission_grants(roles), preferred_username=None, email=None, raw={},
    )


@pytest.fixture(scope="module")
def organizations(owner):
    tag = secrets.token_hex(3).upper()
    rows = {}
    with owner["admin"].begin() as connection:
        for index, status in enumerate(("ACTIVE", "INACTIVE")):
            row = {"id": uuid4(), "country_id": uuid4(), "identification_type": "NIT",
                   "identification_number": f"8{tag}{index:03d}", "legal_name": f"FABRICANTE {status} {tag} SAS",
                   "trade_name": None, "status": status, "created_by": WHO, "updated_by": WHO}
            connection.execute(text(
                "INSERT INTO public.organization_identities (id, country_id, identification_type, identification_number,"
                " legal_name, trade_name, status, created_by, updated_by) VALUES (:id, :country_id,"
                " :identification_type, :identification_number, :legal_name, :trade_name, :status, :created_by,"
                " :updated_by)"), row)
            rows[status] = row
    return rows


def http_directory(existing: set, calls: list | None = None) -> HTTPPartyIdentityManufacturerDirectory:
    """Party Identity como respondería con esos datos: `200` en cualquier estado, `404` si no existe."""

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        organization = request.url.path.rsplit("/", 1)[-1]
        if organization in existing:
            return httpx.Response(200, json={"id": organization})
        return httpx.Response(404, json={})

    return HTTPPartyIdentityManufacturerDirectory(base_url="http://pi.test/api/v1", authorization="Bearer x",
                                                  trace_id=None, timeout_seconds=2,
                                                  transport=httpx.MockTransport(handler))


# --------------------------------------------------------------------------- adaptador


def test_exists_matches_http(owner, organizations):
    double = http_directory({str(row["id"]) for row in organizations.values()})
    contract = ContractPartyIdentityManufacturerDirectory(engine=owner["reader"], claims=claims(ORGANIZATIONS_READ))
    for row in organizations.values():
        assert double.exists(row["id"]) is True
        assert contract.exists(row["id"]) is True
    missing = uuid4()
    assert double.exists(missing) is False
    assert contract.exists(missing) is False


@pytest.mark.parametrize("roles", [(), ("perm:party-identity:person_identities:read",), None])
def test_without_permission_is_access_denied(owner, organizations, roles):
    contract = ContractPartyIdentityManufacturerDirectory(
        engine=owner["reader"], claims=None if roles is None else claims(*roles)
    )
    with pytest.raises(ManufacturerDirectoryAccessDeniedError):
        contract.exists(organizations["ACTIVE"]["id"])


def test_global_permission_covers_the_route(owner, organizations):
    contract = ContractPartyIdentityManufacturerDirectory(engine=owner["reader"],
                                                          claims=claims("perm:party-identity:all:all"))
    assert contract.exists(organizations["ACTIVE"]["id"]) is True


def test_database_down_is_unavailable():
    engine = create_contract_engine(down_settings(), application_name="pc-t071")
    try:
        contract = ContractPartyIdentityManufacturerDirectory(engine=engine, claims=claims(ORGANIZATIONS_READ))
        with pytest.raises(ManufacturerDirectoryUnavailableError) as info:
            contract.exists(uuid4())
        assert "contract:" in str(info.value)
    finally:
        engine.dispose()


# --------------------------------------------------------------------------- de punta a punta


def _client(settings: Settings, test_auth):
    from tests.storage_fakes import FakeAssetStorage

    return TestClient(create_app(settings, auth=test_auth, asset_storage=FakeAssetStorage()))


def _settings(test_database_url: str, reads: ContractReadSettings | None) -> Settings:
    return Settings(docs_enabled=True, database_url=test_database_url,
                    party_identity_service_base_url="http://party-identity.invalid.test",
                    party_identity_timeout_seconds=1.0, party_identity_reads=reads)


def test_create_product_with_contract_manufacturer(owner, organizations, test_database_url, clean_database, test_auth,
                                                   make_token, session_factory):
    unit = factories.unit(session_factory, "UND")
    body = {"product_type": "GOOD", "canonical_name": "Arroz blanco 500 g", "base_unit_id": str(unit.id)}
    with _client(_settings(test_database_url, owner["settings"]), test_auth) as client:
        allowed = ApiClient(client, make_token("perm:product-catalog:all:all", ORGANIZATIONS_READ))
        created = allowed.post("/api/v1/products", json={
            **body, "manufacturer_organization_id": str(organizations["INACTIVE"]["id"])})
        assert created.status_code == 201, created.text
        assert created.json()["manufacturer_organization_id"] == str(organizations["INACTIVE"]["id"])

        missing = allowed.post("/api/v1/products", json={
            **body, "canonical_name": "Otro", "manufacturer_organization_id": str(uuid4())})
        assert missing.status_code == 422
        assert missing.json()["code"] == "PRODUCT_CATALOG.MANUFACTURER_NOT_FOUND"

        denied = ApiClient(client, make_token("perm:product-catalog:all:all")).post("/api/v1/products", json={
            **body, "canonical_name": "Otro", "manufacturer_organization_id": str(organizations["ACTIVE"]["id"])})
        assert denied.status_code == 403
        assert denied.json()["code"] == "PRODUCT_CATALOG.MANUFACTURER_ACCESS_DENIED"

    with _client(_settings(test_database_url, down_settings()), test_auth) as client:
        allowed = ApiClient(client, make_token("perm:product-catalog:all:all", ORGANIZATIONS_READ))
        down = allowed.post("/api/v1/products", json={
            **body, "canonical_name": "Otro", "manufacturer_organization_id": str(organizations["ACTIVE"]["id"])})
        assert down.status_code == 503
        assert down.json()["code"] == "PRODUCT_CATALOG.DEPENDENCY_UNAVAILABLE"


def test_http_source_keeps_http_adapter(test_database_url, clean_database, test_auth):
    """Con `PARTY_IDENTITY_READ_SOURCE=http` (por defecto) la fábrica sigue entregando el adaptador HTTP."""
    settings = _settings(test_database_url, None)
    app = create_app(settings, auth=test_auth)
    directory = app.state.manufacturer_directory_factory(_FakeRequest())
    assert isinstance(directory, HTTPPartyIdentityManufacturerDirectory)


class _FakeRequest:
    class state:  # noqa: N801
        trace_id = None

    headers: dict = {}
