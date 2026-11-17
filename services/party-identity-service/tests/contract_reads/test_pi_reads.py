"""Adaptadores de contrato de Party Identity frente a sus adaptadores HTTP con los mismos datos (spec 025, T069).

Crea en el contenedor de pruebas de Party Identity la base ``party_identity_test__geo`` con las migraciones reales
de Geography y el rol ``pi_contract_reader`` con su ``contract/grants.yaml``, y comprueba:

- ``ContractGeographyLocationDirectory`` (``get_country``, ``get_administrative_division``, ``get_city``) y
  ``ContractGeographyCountryValidator.exists`` dan lo mismo que sus adaptadores HTTP cuando Geography responde lo
  que respondería con esos datos (filas activas e inactivas, ciudad sin división); "no encontrado" igual que el
  ``404``;
- sin el permiso de la ruta en el token, o sin token, la misma ``DependencyUnavailableError`` (dependencia y causa
  ``COUNTRY_VALIDATION_DENIED``) que hoy producen el ``403`` y el ``401`` (FR-037);
- ``find_id_by_iso3`` sigue por API (FR-036);
- base detenida → la misma ``DependencyUnavailableError("geography")`` que hoy produce el ``503``, con causa
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

from party_identity_service.application.exceptions import (
    COUNTRY_VALIDATION_DENIED,
    DependencyUnavailableError,
)
from party_identity_service.infrastructure.contract_geography import (
    ContractGeographyCountryValidator,
    ContractGeographyLocationDirectory,
)
from party_identity_service.infrastructure.geography_country_validator import HTTPGeographyCountryValidator
from party_identity_service.infrastructure.geography_location_directory import HTTPGeographyLocationDirectory

SERVICES = Path(__file__).resolve().parents[3]
OWNER = SERVICES / "geography-service"
DATABASE = "party_identity_test__geo"
CONSUMER = "party-identity"
WHO = "prueba-spec-025"
BASE = "http://geography.test"

COUNTRIES_READ = "perm:geography:global_countries:read"
DIVISIONS_READ = "perm:geography:global_administrative_divisions:read"
CITIES_READ = "perm:geography:global_cities:read"
ALL_READS = (COUNTRIES_READ, DIVISIONS_READ, CITIES_READ)


@pytest.fixture(scope="module")
def owner(test_database_url):
    url = create_owner_schema(test_database_url, DATABASE, OWNER, recreate=True)
    reader_url = provision_reader(url, OWNER / "contract" / "grants.yaml", CONSUMER, secrets.token_urlsafe(24))
    settings = ContractReadSettings(prefix="GEOGRAPHY", source="contract", database_url=reader_url, timeout_seconds=2)
    result = {"admin": create_engine(url), "reader": create_contract_engine(settings, application_name="t069")}
    yield result
    result["admin"].dispose()
    result["reader"].dispose()


def claims(*roles: str) -> TokenClaims:
    return TokenClaims(
        subject=f"sub-{uuid4()}", issuer="test", audiences=("sio-api",),
        expires_at=datetime.now(UTC) + timedelta(minutes=5), roles=frozenset(roles),
        permissions=extract_permission_grants(roles), preferred_username=None, email=None, raw={},
    )


def routed(routes: dict, calls: list, *, status: int | None = None):
    """Doble HTTP: `(método, ruta)` → `(estado, cuerpo)`; lo demás `404`. Con `status`, todas responden ese estado."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.url.path, dict(request.url.params)))
        if status is not None:
            return httpx.Response(status, json={})
        code, body = routes.get((request.method, request.url.path), (404, {}))
        return httpx.Response(code, json=body)

    return httpx.MockTransport(handler)


def http(cls, routes: dict | None = None, *, status: int | None = None, calls: list | None = None):
    return cls(base_url=BASE, authorization="Bearer x", timeout_seconds=2,
               transport=routed(routes or {}, [] if calls is None else calls, status=status))


def insert(owner, table: str, **values) -> dict:
    columns = ", ".join(values)
    marks = ", ".join(f":{name}" for name in values)
    with owner["admin"].begin() as connection:
        connection.execute(text(f"INSERT INTO public.{table} ({columns}) VALUES ({marks})"), values)
    return values


def audit() -> dict:
    return {"created_by": WHO, "updated_by": WHO}


def as_json(row: dict) -> dict:
    return {key: (str(value) if isinstance(value, UUID) else value) for key, value in row.items()}


@pytest.fixture(scope="module")
def geo(owner):
    """Países, divisiones y ciudades en ambos estados; una ciudad sin división."""
    active = insert(owner, "global_countries", id=uuid4(), iso2_code="ZZ", iso3_code="ZZZ", name="PAÍS FICTICIO",
                    status="ACTIVE", **audit())
    inactive = insert(owner, "global_countries", id=uuid4(), iso2_code="ZY", iso3_code="ZZY",
                      name="PAÍS FICTICIO INACTIVO", status="INACTIVE", **audit())
    divisions = [
        insert(owner, "global_administrative_divisions", id=uuid4(), country_id=active["id"], code="D1",
               name="DIVISIÓN FICTICIA", division_type="DEPARTMENT", status="ACTIVE", **audit()),
        insert(owner, "global_administrative_divisions", id=uuid4(), country_id=inactive["id"], code="D2",
               name="DIVISIÓN INACTIVA", division_type="STATE", status="INACTIVE", **audit()),
    ]
    cities = [
        insert(owner, "global_cities", id=uuid4(), country_id=active["id"], administrative_division_id=divisions[0]["id"],
               code="C1", name="CIUDAD FICTICIA", status="ACTIVE", **audit()),
        insert(owner, "global_cities", id=uuid4(), country_id=inactive["id"],
               administrative_division_id=divisions[1]["id"], code="C2", name="CIUDAD INACTIVA", status="INACTIVE",
               **audit()),
        insert(owner, "global_cities", id=uuid4(), country_id=active["id"], administrative_division_id=None,
               name="CIUDAD SIN DIVISIÓN", status="ACTIVE", **audit()),
    ]
    routes = {}
    for prefix, rows in (("global-countries", [active, inactive]), ("global-administrative-divisions", divisions),
                         ("global-cities", cities)):
        for row in rows:
            routes[("GET", f"/{prefix}/{row['id']}")] = (200, as_json(row))
    return {"countries": [active, inactive], "divisions": divisions, "cities": cities, "routes": routes}


# --------------------------------------------------------------------------- LocationDirectory


def test_location_directory_matches_http(owner, geo):
    contract = ContractGeographyLocationDirectory(engine=owner["reader"], claims=claims(*ALL_READS))
    double = http(HTTPGeographyLocationDirectory, geo["routes"])
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
def test_location_without_permission_is_denied_like_http(owner, geo, method, granted, status):
    contract = ContractGeographyLocationDirectory(engine=owner["reader"], claims=claims(*granted) if status == 403 else None)
    double = http(HTTPGeographyLocationDirectory, status=status)
    row_id = geo["cities"][0]["id"]
    with pytest.raises(DependencyUnavailableError) as expected:
        getattr(double, method)(row_id)
    with pytest.raises(DependencyUnavailableError) as info:
        getattr(contract, method)(row_id)
    assert (info.value.dependency, info.value.cause) == (expected.value.dependency, expected.value.cause) == (
        "geography", COUNTRY_VALIDATION_DENIED,
    )


# --------------------------------------------------------------------------- CountryDirectory


def validator(owner, token: TokenClaims | None, *, routes: dict | None = None, status: int | None = None,
              calls: list | None = None) -> ContractGeographyCountryValidator:
    return ContractGeographyCountryValidator(
        engine=owner["reader"], claims=token,
        http=http(HTTPGeographyCountryValidator, routes, status=status, calls=calls),
    )


def test_country_exists_matches_http(owner, geo):
    calls: list = []
    contract = validator(owner, claims(COUNTRIES_READ), calls=calls)
    double = http(HTTPGeographyCountryValidator, geo["routes"])
    for row in geo["countries"]:  # activo e inactivo: el `200` de hoy no mira el estado
        assert contract.exists(row["id"]) is double.exists(row["id"]) is True
    missing = uuid4()
    assert contract.exists(missing) is double.exists(missing) is False
    assert calls == []  # ninguna solicitud a Geography


@pytest.mark.parametrize("status", [403, 401])
def test_country_exists_without_permission_is_denied_like_http(owner, geo, status):
    token = claims(DIVISIONS_READ, CITIES_READ) if status == 403 else None
    with pytest.raises(DependencyUnavailableError) as expected:
        http(HTTPGeographyCountryValidator, status=status).exists(geo["countries"][0]["id"])
    with pytest.raises(DependencyUnavailableError) as info:
        validator(owner, token).exists(geo["countries"][0]["id"])
    assert (info.value.dependency, info.value.cause) == (expected.value.dependency, expected.value.cause) == (
        "geography", COUNTRY_VALIDATION_DENIED,
    )


def test_find_id_by_iso3_still_goes_through_the_api(owner, geo):
    """FR-036: la búsqueda por ISO3 no se lee de la vista; va a `GET /global-countries?iso3_code=`."""
    calls: list = []
    country = geo["countries"][0]
    routes = {("GET", "/global-countries"): (200, {"items": [{"id": str(country["id"]), "iso3_code": "ZZZ"}]})}
    found = validator(owner, None, routes=routes, calls=calls).find_id_by_iso3("ZZZ")
    assert found == country["id"]
    assert calls == [("/global-countries", {"iso3_code": "ZZZ"})]


# --------------------------------------------------------------------------- base detenida


def down_engine():
    settings = ContractReadSettings(
        prefix="GEOGRAPHY", source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url=f"postgresql+psycopg://pi_contract_reader:x@127.0.0.1:1/{DATABASE}",
    )
    return create_contract_engine(settings, application_name="t069")


@pytest.mark.parametrize(
    ("call", "http_call"),
    [
        (lambda e: ContractGeographyLocationDirectory(engine=e, claims=claims(*ALL_READS)).get_country(uuid4()),
         lambda: http(HTTPGeographyLocationDirectory, status=503).get_country(uuid4())),
        (lambda e: ContractGeographyLocationDirectory(engine=e, claims=claims(*ALL_READS))
         .get_administrative_division(uuid4()),
         lambda: http(HTTPGeographyLocationDirectory, status=503).get_administrative_division(uuid4())),
        (lambda e: ContractGeographyLocationDirectory(engine=e, claims=claims(*ALL_READS)).get_city(uuid4()),
         lambda: http(HTTPGeographyLocationDirectory, status=503).get_city(uuid4())),
        (lambda e: ContractGeographyCountryValidator(engine=e, claims=claims(*ALL_READS),
                                                     http=http(HTTPGeographyCountryValidator)).exists(uuid4()),
         lambda: http(HTTPGeographyCountryValidator, status=503).exists(uuid4())),
    ],
    ids=["get_country", "get_administrative_division", "get_city", "exists"],
)
def test_database_down_is_unavailable_like_http_503(call, http_call):
    with pytest.raises(DependencyUnavailableError) as expected:
        http_call()
    engine = down_engine()
    try:
        with pytest.raises(DependencyUnavailableError) as info:
            call(engine)
        assert info.value.dependency == expected.value.dependency == "geography"
        assert info.value.cause.startswith("contract:")
    finally:
        engine.dispose()


# --------------------------------------------------------------------------- selección en main.py


def test_factories_select_contract_with_engine_and_http_without(owner, geo):
    from starlette.requests import Request

    from party_identity_service.config import Settings
    from party_identity_service.main import build_country_directory_factory, build_location_directory_factory

    settings = Settings(docs_enabled=False, database_url="postgresql+psycopg://x@localhost/x",
                        geography_service_base_url=BASE)
    request = Request({"type": "http", "headers": [(b"authorization", b"Bearer x")],
                       "state": {"sio_claims": claims(COUNTRIES_READ)}})
    locations = build_location_directory_factory(settings, owner["reader"])(request)
    assert isinstance(locations, ContractGeographyLocationDirectory)
    assert locations.get_country(geo["countries"][0]["id"]).status == "ACTIVE"
    countries = build_country_directory_factory(settings, owner["reader"])(request)
    assert isinstance(countries, ContractGeographyCountryValidator)
    assert countries.exists(geo["countries"][1]["id"]) is True
    assert isinstance(build_location_directory_factory(settings)(request), HTTPGeographyLocationDirectory)
    assert isinstance(build_country_directory_factory(settings)(request), HTTPGeographyCountryValidator)


def test_read_source_defaults_to_http(monkeypatch):
    from party_identity_service.config import load_settings

    monkeypatch.delenv("GEOGRAPHY_READ_SOURCE", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://x@localhost/x")
    assert not load_settings().geography_reads.uses_contract
    monkeypatch.setenv("GEOGRAPHY_READ_SOURCE", "contract")
    monkeypatch.delenv("GEOGRAPHY_CONTRACT_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="GEOGRAPHY_CONTRACT_DATABASE_URL"):
        load_settings()
