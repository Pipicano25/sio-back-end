"""Adaptadores de contrato de Operational Context frente a sus adaptadores HTTP con los mismos datos (spec 025, T068).

Crea en el contenedor de pruebas de Operational Context las bases ``operational_context_test__geo`` y
``operational_context_test__pi`` con las migraciones reales de Geography y Party Identity, el rol
``oc_contract_reader`` con su ``contract/grants.yaml`` (una sola contraseña: el rol es del servidor) y comprueba, para
cada método de ``ContractGeographyDirectory``, ``ContractPartyIdentityPersonDirectory`` y
``ContractPartyIdentityOrganizationDirectory``:

- mismo resultado que el adaptador HTTP cuando el propietario responde lo que respondería con esos datos (filas
  activas e inactivas, ciudad sin división, textos vacíos);
- "no encontrado" igual que el ``404`` de hoy;
- sin el permiso de la ruta en el token, o sin token, la misma ``DependencyUnavailableError`` (proveedor y causa de
  denegación) que hoy producen el ``403`` y el ``401`` (FR-037);
- base detenida → la misma ``DependencyUnavailableError(<proveedor>)`` que hoy produce el ``503``, con causa
  ``contract:``.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sio_auth import TokenClaims
from sio_auth.permissions import extract_permission_grants
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sqlalchemy import create_engine, text

from operational_context_service.application.exceptions import (
    GEOGRAPHY_VALIDATION_DENIED,
    ORGANIZATION_VALIDATION_DENIED,
    PERSON_VALIDATION_DENIED,
    DependencyUnavailableError,
)
from operational_context_service.infrastructure.contract_geography import ContractGeographyDirectory
from operational_context_service.infrastructure.contract_party_identity import (
    ContractPartyIdentityOrganizationDirectory,
    ContractPartyIdentityPersonDirectory,
)
from operational_context_service.infrastructure.geography_directory import HTTPGeographyDirectory
from operational_context_service.infrastructure.party_identity_organization_directory import (
    HTTPPartyIdentityOrganizationDirectory,
)
from operational_context_service.infrastructure.party_identity_person_directory import (
    HTTPPartyIdentityPersonDirectory,
)

SERVICES = Path(__file__).resolve().parents[3]
OWNERS = {"geo": "geography-service", "pi": "party-identity-service"}
DATABASES = {"geo": "operational_context_test__geo", "pi": "operational_context_test__pi"}
OWNER_ENV = {"PARTY_IDENTITY_SEED_COUNTRY_ID": "6f1c1b54-0d0e-4a63-9a8c-6f0f8f7f1a11"}
CONSUMER = "operational-context"
WHO = "prueba-spec-025"

COUNTRIES_READ = "perm:geography:global_countries:read"
DIVISIONS_READ = "perm:geography:global_administrative_divisions:read"
CITIES_READ = "perm:geography:global_cities:read"
PERSONS_READ = "perm:party-identity:person_identities:read"
ORGANIZATIONS_READ = "perm:party-identity:organization_identities:read"
ALL_READS = (COUNTRIES_READ, DIVISIONS_READ, CITIES_READ, PERSONS_READ, ORGANIZATIONS_READ)


# --------------------------------------------------------------------------- infraestructura


@pytest.fixture(scope="module")
def owners(test_database_url):
    result = {}
    # Los roles son del servidor: las dos bases comparten `oc_contract_reader` y su contraseña.
    password = secrets.token_urlsafe(24)
    for key, service in OWNERS.items():
        owner = SERVICES / service
        url = create_owner_schema(test_database_url, DATABASES[key], owner, OWNER_ENV, recreate=True)
        reader_url = provision_reader(url, owner / "contract" / "grants.yaml", CONSUMER, password)
        settings = ContractReadSettings(prefix=key.upper(), source="contract", database_url=reader_url, timeout_seconds=2)
        result[key] = {"admin": create_engine(url), "reader": create_contract_engine(settings, application_name="t068")}
    yield result
    for item in result.values():
        item["admin"].dispose()
        item["reader"].dispose()


def claims(*roles: str) -> TokenClaims:
    return TokenClaims(
        subject=f"sub-{uuid4()}", issuer="test", audiences=("sio-api",),
        expires_at=datetime.now(UTC) + timedelta(minutes=5), roles=frozenset(roles),
        permissions=extract_permission_grants(roles), preferred_username=None, email=None, raw={},
    )


def routed(routes: dict, *, status: int | None = None):
    """Doble HTTP: `(método, ruta)` → cuerpo `200`; lo demás `404`. Con `status`, todas responden ese estado."""

    def handler(request: httpx.Request) -> httpx.Response:
        if status is not None:
            return httpx.Response(status, json={})
        key = (request.method, request.url.path)
        if key not in routes:
            return httpx.Response(404, json={})
        return httpx.Response(200, json=routes[key])

    return httpx.MockTransport(handler)


def http(cls, base_url: str, routes: dict, *, status: int | None = None):
    return cls(base_url=base_url, authorization="Bearer x", timeout_seconds=2, transport=routed(routes, status=status))


def insert(owners, key: str, table: str, **values) -> dict:
    columns = ", ".join(values)
    marks = ", ".join(f":{name}" for name in values)
    with owners[key]["admin"].begin() as connection:
        connection.execute(text(f"INSERT INTO public.{table} ({columns}) VALUES ({marks})"), values)
    return values


def audit() -> dict:
    return {"created_by": WHO, "updated_by": WHO}


def as_json(row: dict) -> dict:
    return {key: (str(value) if isinstance(value, UUID) else value) for key, value in row.items()}


# --------------------------------------------------------------------------- Geography


GEO_BASE = "http://geography.test"


@pytest.fixture(scope="module")
def geo(owners):
    """Países, divisiones y ciudades en ambos estados; una ciudad sin división."""
    active = insert(owners, "geo", "global_countries", id=uuid4(), iso2_code="ZZ", iso3_code="ZZZ", name="PAÍS FICTICIO",
                    status="ACTIVE", **audit())
    inactive = insert(owners, "geo", "global_countries", id=uuid4(), iso2_code="ZY", iso3_code="ZZY",
                      name="PAÍS FICTICIO INACTIVO", status="INACTIVE", **audit())
    divisions = [
        insert(owners, "geo", "global_administrative_divisions", id=uuid4(), country_id=active["id"], code="D1",
               name="DIVISIÓN FICTICIA", division_type="DEPARTMENT", status="ACTIVE", **audit()),
        insert(owners, "geo", "global_administrative_divisions", id=uuid4(), country_id=inactive["id"], code="D2",
               name="DIVISIÓN INACTIVA", division_type="STATE", status="INACTIVE", **audit()),
    ]
    cities = [
        insert(owners, "geo", "global_cities", id=uuid4(), country_id=active["id"],
               administrative_division_id=divisions[0]["id"], code="C1", name="CIUDAD FICTICIA", status="ACTIVE",
               **audit()),
        insert(owners, "geo", "global_cities", id=uuid4(), country_id=inactive["id"],
               administrative_division_id=divisions[1]["id"], code="C2", name="CIUDAD INACTIVA", status="INACTIVE",
               **audit()),
        insert(owners, "geo", "global_cities", id=uuid4(), country_id=active["id"], administrative_division_id=None,
               name="CIUDAD SIN DIVISIÓN", status="ACTIVE", **audit()),
    ]
    return {"countries": [active, inactive], "divisions": divisions, "cities": cities}


def geo_routes(geo) -> dict:
    """Lo que respondería Geography (`GET` por id) con esos datos."""
    routes = {}
    for prefix, rows in (("global-countries", geo["countries"]), ("global-administrative-divisions", geo["divisions"]),
                         ("global-cities", geo["cities"])):
        for row in rows:
            routes[("GET", f"/{prefix}/{row['id']}")] = as_json(row)
    return routes


def test_geography_directory_matches_http(owners, geo):
    contract = ContractGeographyDirectory(engine=owners["geo"]["reader"], claims=claims(*ALL_READS))
    double = http(HTTPGeographyDirectory, GEO_BASE, geo_routes(geo))
    for row in geo["countries"]:
        assert contract.get_country(row["id"]) == double.get_country(row["id"]) is not None
    for row in geo["divisions"]:
        assert contract.get_administrative_division(row["id"]) == double.get_administrative_division(row["id"]) is not None
    for row in geo["cities"]:
        assert contract.get_city(row["id"]) == double.get_city(row["id"]) is not None
    assert contract.get_city(geo["cities"][2]["id"]).administrative_division_id is None
    assert {contract.get_country(row["id"]).status for row in geo["countries"]} == {"ACTIVE", "INACTIVE"}

    missing = uuid4()
    for method in ("get_country", "get_administrative_division", "get_city"):
        assert getattr(contract, method)(missing) is None
        assert getattr(double, method)(missing) is None


@pytest.mark.parametrize(
    ("method", "granted"),
    [
        ("get_country", (DIVISIONS_READ, CITIES_READ)),
        ("get_administrative_division", (COUNTRIES_READ, CITIES_READ)),
        ("get_city", (COUNTRIES_READ, DIVISIONS_READ)),
    ],
)
@pytest.mark.parametrize("status", [403, 401])
def test_geography_without_permission_is_denied_like_http(owners, geo, method, granted, status):
    """Sin el permiso de esa ruta (`403`) o sin token (`401`): la misma denegación que hoy (FR-037)."""
    token = claims(*granted) if status == 403 else None
    contract = ContractGeographyDirectory(engine=owners["geo"]["reader"], claims=token)
    double = http(HTTPGeographyDirectory, GEO_BASE, {}, status=status)
    row_id = geo["cities"][0]["id"]
    with pytest.raises(DependencyUnavailableError) as expected:
        getattr(double, method)(row_id)
    with pytest.raises(DependencyUnavailableError) as info:
        getattr(contract, method)(row_id)
    assert (info.value.provider, info.value.cause, info.value.operation) == (
        expected.value.provider, expected.value.cause, expected.value.operation,
    ) == ("geography", GEOGRAPHY_VALIDATION_DENIED, method)


def test_geography_wildcard_permission_is_accepted(owners, geo):
    contract = ContractGeographyDirectory(engine=owners["geo"]["reader"], claims=claims("perm:geography:all:read"))
    assert contract.get_city(geo["cities"][0]["id"]) is not None


# --------------------------------------------------------------------------- Party Identity


PI_BASE = "http://party-identity.test/api/v1"


@pytest.fixture(scope="module")
def parties(owners):
    tag = secrets.token_hex(3).upper()
    country = uuid4()
    people = [
        insert(owners, "pi", "person_identities", id=uuid4(), identification_country_id=country,
               identification_type="CC", identification_number=f"{tag}{index:04d}", first_name=first,
               middle_name=middle, last_name="PRUEBA", second_last_name=second, status=status,
               verification_status="UNVERIFIED", **audit())
        for index, (first, middle, second, status) in enumerate(
            (("ANA", "MARÍA", "GÓMEZ", "ACTIVE"), ("LUIS", None, None, "INACTIVE"))
        )
    ]
    organizations = [
        insert(owners, "pi", "organization_identities", id=uuid4(), country_id=country, identification_type="NIT",
               identification_number=f"9{tag}{index:03d}", legal_name=f"EMPRESA FICTICIA {index} {tag} SAS",
               trade_name=trade, status=status, **audit())
        for index, (trade, status) in enumerate((("FICTICIA", "ACTIVE"), (None, "INACTIVE")))
    ]
    return {"people": people, "organizations": organizations}


def person_body(row: dict) -> dict:
    """`GET /person-identities/{id}` con esos datos (campos que lee el adaptador)."""
    keys = ("id", "identification_type", "identification_number", "first_name", "middle_name", "last_name",
            "second_last_name", "status")
    return as_json({key: row.get(key) for key in keys})


def organization_body(row: dict) -> dict:
    keys = ("id", "identification_type", "identification_number", "legal_name", "trade_name", "status")
    return as_json({key: row.get(key) for key in keys})


def pi_routes(parties) -> dict:
    routes = {("GET", f"/api/v1/person-identities/{row['id']}"): person_body(row) for row in parties["people"]}
    routes.update(
        {("GET", f"/api/v1/organization-identities/{row['id']}"): organization_body(row)
         for row in parties["organizations"]}
    )
    return routes


def test_person_directory_matches_http(owners, parties):
    contract = ContractPartyIdentityPersonDirectory(engine=owners["pi"]["reader"], claims=claims(*ALL_READS))
    double = http(HTTPPartyIdentityPersonDirectory, PI_BASE, pi_routes(parties))
    for row in parties["people"]:
        assert contract.get_person(row["id"]) == double.get_person(row["id"]) is not None
        assert contract.get_person_profile(row["id"]) == double.get_person_profile(row["id"]) is not None
    assert contract.get_person_profile(parties["people"][1]["id"]).middle_name is None
    missing = uuid4()
    assert contract.get_person(missing) is None and double.get_person(missing) is None
    assert contract.get_person_profile(missing) is None and double.get_person_profile(missing) is None


def test_organization_directory_matches_http(owners, parties):
    contract = ContractPartyIdentityOrganizationDirectory(engine=owners["pi"]["reader"], claims=claims(*ALL_READS))
    double = http(HTTPPartyIdentityOrganizationDirectory, PI_BASE, pi_routes(parties))
    for row in parties["organizations"]:
        assert contract.get_organization(row["id"]) == double.get_organization(row["id"]) is not None
        assert contract.get_organization_profile(row["id"]) == double.get_organization_profile(row["id"]) is not None
    assert contract.get_organization_profile(parties["organizations"][1]["id"]).trade_name is None
    missing = uuid4()
    assert contract.get_organization(missing) is None and double.get_organization(missing) is None
    assert contract.get_organization_profile(missing) is None and double.get_organization_profile(missing) is None


@pytest.mark.parametrize(
    ("cls", "http_cls", "method", "granted", "cause"),
    [
        (ContractPartyIdentityPersonDirectory, HTTPPartyIdentityPersonDirectory, "get_person", ORGANIZATIONS_READ,
         PERSON_VALIDATION_DENIED),
        (ContractPartyIdentityPersonDirectory, HTTPPartyIdentityPersonDirectory, "get_person_profile",
         ORGANIZATIONS_READ, PERSON_VALIDATION_DENIED),
        (ContractPartyIdentityOrganizationDirectory, HTTPPartyIdentityOrganizationDirectory, "get_organization",
         PERSONS_READ, ORGANIZATION_VALIDATION_DENIED),
        (ContractPartyIdentityOrganizationDirectory, HTTPPartyIdentityOrganizationDirectory,
         "get_organization_profile", PERSONS_READ, ORGANIZATION_VALIDATION_DENIED),
    ],
)
@pytest.mark.parametrize("status", [403, 401])
def test_party_identity_without_permission_is_denied_like_http(owners, parties, cls, http_cls, method, granted, cause,
                                                                status):
    token = claims(granted) if status == 403 else None
    contract = cls(engine=owners["pi"]["reader"], claims=token)
    double = http(http_cls, PI_BASE, {}, status=status)
    row_id = parties["people"][0]["id"]
    with pytest.raises(DependencyUnavailableError) as expected:
        getattr(double, method)(row_id)
    with pytest.raises(DependencyUnavailableError) as info:
        getattr(contract, method)(row_id)
    assert (info.value.provider, info.value.cause, info.value.operation) == (
        expected.value.provider, expected.value.cause, expected.value.operation,
    ) == ("party-identity", cause, method)


# --------------------------------------------------------------------------- base detenida


def down_engine(key: str):
    settings = ContractReadSettings(
        prefix=key.upper(), source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url=f"postgresql+psycopg://oc_contract_reader:x@127.0.0.1:1/{DATABASES[key]}",
    )
    return create_contract_engine(settings, application_name="t068")


def _geo(engine):
    return ContractGeographyDirectory(engine=engine, claims=claims(*ALL_READS))


def _person(engine):
    return ContractPartyIdentityPersonDirectory(engine=engine, claims=claims(*ALL_READS))


def _organization(engine):
    return ContractPartyIdentityOrganizationDirectory(engine=engine, claims=claims(*ALL_READS))


GEO, PERSON, ORGANIZATION = HTTPGeographyDirectory, HTTPPartyIdentityPersonDirectory, HTTPPartyIdentityOrganizationDirectory


@pytest.mark.parametrize(
    ("key", "contract", "http_cls", "method"),
    [
        ("geo", _geo, GEO, "get_country"),
        ("geo", _geo, GEO, "get_administrative_division"),
        ("geo", _geo, GEO, "get_city"),
        ("pi", _person, PERSON, "get_person"),
        ("pi", _person, PERSON, "get_person_profile"),
        ("pi", _organization, ORGANIZATION, "get_organization"),
        ("pi", _organization, ORGANIZATION, "get_organization_profile"),
    ],
)
def test_database_down_is_unavailable_like_http_503(key, contract, http_cls, method):
    with pytest.raises(DependencyUnavailableError) as expected:
        getattr(http(http_cls, "http://owner.test", {}, status=503), method)(uuid4())
    engine = down_engine(key)
    try:
        with pytest.raises(DependencyUnavailableError) as info:
            getattr(contract(engine), method)(uuid4())
        assert info.value.provider == expected.value.provider
        assert info.value.operation == expected.value.operation == method
        assert info.value.cause.startswith("contract:")
    finally:
        engine.dispose()


# --------------------------------------------------------------------------- selección en main.py


def test_factories_select_contract_with_engine_and_http_without(owners, geo):
    """Con motor (`<PROP>_READ_SOURCE=contract`) se usa el adaptador de contrato con los `TokenClaims` de la
    solicitud; sin motor (`http`, por defecto) el adaptador HTTP de siempre."""
    from starlette.requests import Request

    from operational_context_service.config import Settings
    from operational_context_service.main import (
        build_geography_directory_factory,
        build_organization_directory_factory,
        build_person_directory_factory,
    )

    settings = Settings(docs_enabled=False, database_url="postgresql+psycopg://x@localhost/x",
                        party_identity_base_url=PI_BASE, geography_base_url=GEO_BASE, keycloak_base_url="http://kc",
                        keycloak_client_id="x", keycloak_client_secret="x")
    request = Request({"type": "http", "headers": [(b"authorization", b"Bearer x")],
                       "state": {"sio_claims": claims(COUNTRIES_READ)}})
    geography = build_geography_directory_factory(settings, owners["geo"]["reader"])(request)
    assert isinstance(geography, ContractGeographyDirectory)
    assert geography.get_country(geo["countries"][0]["id"]).status == "ACTIVE"
    assert isinstance(build_person_directory_factory(settings, owners["pi"]["reader"])(request),
                      ContractPartyIdentityPersonDirectory)
    assert isinstance(build_organization_directory_factory(settings, owners["pi"]["reader"])(request),
                      ContractPartyIdentityOrganizationDirectory)
    assert isinstance(build_geography_directory_factory(settings)(request), HTTPGeographyDirectory)
    assert isinstance(build_person_directory_factory(settings)(request), HTTPPartyIdentityPersonDirectory)
    assert isinstance(build_organization_directory_factory(settings)(request), HTTPPartyIdentityOrganizationDirectory)


def test_read_source_defaults_to_http(monkeypatch):
    from operational_context_service.config import load_settings

    for name in ("PARTY_IDENTITY_READ_SOURCE", "GEOGRAPHY_READ_SOURCE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x@localhost/x")
    monkeypatch.setenv("KEYCLOAK_BASE_URL", "http://kc")
    monkeypatch.setenv("OPERATIONAL_CONTEXT_CLIENT_ID", "x")
    monkeypatch.setenv("OPERATIONAL_CONTEXT_CLIENT_SECRET", "x")
    settings = load_settings()
    assert not settings.party_identity_reads.uses_contract
    assert not settings.geography_reads.uses_contract
    monkeypatch.setenv("GEOGRAPHY_READ_SOURCE", "contract")
    monkeypatch.delenv("GEOGRAPHY_CONTRACT_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="GEOGRAPHY_CONTRACT_DATABASE_URL"):
        load_settings()
