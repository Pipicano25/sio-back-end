"""Resumen de empresas por vistas de contrato frente a sus adaptadores HTTP con los mismos datos (spec 025, T062).

Crea en el contenedor de pruebas de Commercial Relationship las bases ``commercial_relationship_test__sum_{oc,pi}``
con las migraciones reales de Operational Context y Party Identity, el rol ``cr_contract_reader`` con su
``contract/grants.yaml`` (una sola contraseña por ejecución: los roles son del servidor), y comprueba:

- ``ContractCompanyAccessDirectory.list_member_companies``, ``ContractCompanyDirectory`` y
  ``ContractPartyDirectory`` devuelven lo mismo que el adaptador HTTP cuando el propietario responde lo que
  respondería con esos datos (membresías en todos los estados, empresa repetida, visibilidad por membresía
  ``ACTIVE``, ``platform:lookup`` y ``platform:administer``);
- "no encontrado" igual que el ``404`` de hoy;
- sin el permiso de la ruta del propietario en el token → la misma excepción (o ``None``) que el ``403`` de hoy;
- base detenida → la misma ``DependencyUnavailableError(<proveedor>)`` que hoy produce el ``503``;
- ``GET /company-summaries`` con ``*_READ_SOURCE=contract`` responde lo mismo que con HTTP, sin ninguna solicitud
  HTTP saliente, y el mismo ``403`` y ``503``.

Los dobles HTTP responden según las reglas del propietario: ``/me/operational-context`` devuelve todas las
membresías (paridad en ``OC/tests/contract_views/test_memberships_parity.py``); ``GET /companies/{id}`` responde
``404`` si la empresa no existe o no es visible (``CompanyService.get`` + ``AccessScope.ensure_company_visible``).
"""

from __future__ import annotations

import dataclasses
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sio_auth import TokenClaims
from sio_auth.permissions import extract_permission_grants
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sqlalchemy import create_engine, text

from commercial_relationship_service.application.exceptions import (
    DependencyUnavailableError,
    NotFoundError,
    OperationalAccessDeniedError,
    PartyIdentityAccessDeniedError,
)
from commercial_relationship_service.infrastructure.contract_operational_context import (
    ContractCompanyAccessDirectory,
    ContractCompanyDirectory,
)
from commercial_relationship_service.infrastructure.contract_party_identity import ContractPartyDirectory
from commercial_relationship_service.infrastructure.operational_context_directory import (
    HTTPCompanyAccessDirectory,
    HTTPCompanyDirectory,
)
from commercial_relationship_service.infrastructure.party_identity_directory import HTTPPartyDirectory
from commercial_relationship_service.main import create_app

SERVICES = Path(__file__).resolve().parents[3]
OWNERS = {"oc": "operational-context-service", "pi": "party-identity-service"}
OWNER_ENV = {"PARTY_IDENTITY_SEED_COUNTRY_ID": "6f1c1b54-0d0e-4a63-9a8c-6f0f8f7f1a11"}
CONSUMER = "commercial-relationship"
WHO = "prueba-spec-025"

MEMBERSHIPS_READ = "perm:operational-context:application_users:read"
COMPANIES_READ = "perm:operational-context:companies:read"
PLATFORM_LOOKUP = "perm:operational-context:platform:lookup"
PLATFORM_ADMINISTER = "perm:operational-context:platform:administer"
PERSONS_READ = "perm:party-identity:person_identities:read"
ORGANIZATIONS_READ = "perm:party-identity:organization_identities:read"
CONTACTS_READ = "perm:party-identity:organization_contact_persons:read"
PRODUCTS_READ = "perm:commercial-relationship:company_products:read"
OWNER_READS = (MEMBERSHIPS_READ, COMPANIES_READ, PERSONS_READ, ORGANIZATIONS_READ, CONTACTS_READ)


# --------------------------------------------------------------------------- infraestructura


@pytest.fixture(scope="module")
def owners(test_database_url):
    """URL de administrador, motor de administrador, URL y motor de lectura de cada propietario."""
    result = {}
    password = secrets.token_urlsafe(24)
    for key, service in OWNERS.items():
        owner = SERVICES / service
        url = create_owner_schema(
            test_database_url, f"commercial_relationship_test__sum_{key}", owner, OWNER_ENV, recreate=True
        )
        reader_url = provision_reader(url, owner / "contract" / "grants.yaml", CONSUMER, password)
        settings = ContractReadSettings(prefix=key.upper(), source="contract", database_url=reader_url, timeout_seconds=2)
        result[key] = {
            "admin": create_engine(url),
            "settings": settings,
            "reader": create_contract_engine(settings, application_name="cr-t062"),
        }
    yield result
    for item in result.values():
        item["admin"].dispose()
        item["reader"].dispose()


def down_settings(key: str) -> ContractReadSettings:
    return ContractReadSettings(
        prefix=key.upper(), source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url=f"postgresql+psycopg://cr_contract_reader:x@127.0.0.1:1/commercial_relationship_test__sum_{key}",
    )


def claims(subject: str, *roles: str) -> TokenClaims:
    return TokenClaims(
        subject=subject, issuer="test", audiences=("sio-api",), expires_at=datetime.now(UTC) + timedelta(minutes=5),
        roles=frozenset(roles), permissions=extract_permission_grants(roles), preferred_username=None, email=None,
        raw={},
    )


def routed(routes: dict, calls: list | None = None):
    """Doble HTTP: `(método, ruta)` → `(estado, cuerpo)`; lo demás `404`."""

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        status, body = routes.get((request.method, request.url.path), (404, {}))
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def http(cls, routes: dict, calls: list | None = None):
    return cls(base_url="http://owner.test/api/v1", authorization="Bearer x", timeout_seconds=2,
               transport=routed(routes, calls))


def insert(owners, key: str, table: str, **values) -> dict:
    columns = ", ".join(values)
    marks = ", ".join(f":{name}" for name in values)
    with owners[key]["admin"].begin() as connection:
        connection.execute(text(f"INSERT INTO public.{table} ({columns}) VALUES ({marks})"), values)
    return values


def audit() -> dict:
    return {"created_by": WHO, "updated_by": WHO}


# --------------------------------------------------------------------------- datos


@pytest.fixture(scope="module")
def world(owners):
    """Un usuario con membresías en todos los estados, la misma empresa repetida y una empresa sin razón social."""
    tag = secrets.token_hex(3).upper()
    country = uuid4()
    sub = f"sub-resumen-{uuid4()}"
    other = f"sub-otro-{uuid4()}"
    companies, organizations = {}, {}

    def company(name: str, status: str = "ACTIVE", *, with_identity: bool = True) -> UUID:
        organization_id = uuid4()
        row = insert(owners, "oc", "companies", id=uuid4(), organization_identity_id=organization_id, status=status,
                     version=1, **audit())
        companies[name] = row
        if with_identity:
            organizations[name] = insert(
                owners, "pi", "organization_identities", id=organization_id, country_id=country,
                identification_type="NIT", identification_number=f"9{tag}{len(organizations):03d}",
                legal_name=f"EMPRESA {name} {tag} SAS", trade_name=None, status="ACTIVE", **audit(),
            )
        return row["id"]

    memberships = []

    def member(company_id: UUID, subject: str, status: str = "ACTIVE", age_days: int = 0) -> None:
        row = insert(owners, "oc", "application_users", id=uuid4(), company_id=company_id, keycloak_user_id=subject,
                     person_identity_id=uuid4(), display_name="Usuario Ficticio", status=status,
                     created_at=datetime.now(UTC) - timedelta(days=age_days), **audit())
        memberships.append(row)

    member(company("ACTIVA"), sub, age_days=5)
    member(company("CERRADA", "INACTIVE"), sub, age_days=1)
    member(company("SIN_MEMBRESIA_ACTIVA"), sub, "INACTIVE", age_days=4)
    repeated = company("REPETIDA")
    member(repeated, sub, age_days=3)
    member(repeated, sub, "INACTIVE", age_days=2)
    member(repeated, sub, "INACTIVE", age_days=6)
    member(company("SIN_RAZON_SOCIAL", with_identity=False), sub, age_days=7)
    member(company("AJENA"), other)

    people = [
        insert(owners, "pi", "person_identities", id=uuid4(), identification_country_id=country,
               identification_type="CC", identification_number=f"{tag}{index:04d}", first_name="ANA",
               middle_name=None, last_name="PRUEBA", second_last_name=None, status=status,
               verification_status="UNVERIFIED", **audit())
        for index, status in enumerate(("ACTIVE", "INACTIVE"))
    ]
    organization_id = organizations["ACTIVA"]["id"]
    contacts = [
        insert(owners, "pi", "organization_contact_persons", id=uuid4(), organization_identity_id=organization_id,
               person_identity_id=people[0]["id"], is_primary=True, is_active=True, **audit()),
        insert(owners, "pi", "organization_contact_persons", id=uuid4(), organization_identity_id=organization_id,
               person_identity_id=None, phone="+57 601 555 0101", is_primary=False, is_active=False, **audit()),
    ]
    inactive_org = insert(owners, "pi", "organization_identities", id=uuid4(), country_id=country,
                          identification_type="NIT", identification_number=f"8{tag}000", legal_name=f"INACTIVA {tag}",
                          trade_name=None, status="INACTIVE", **audit())
    return {"sub": sub, "other": other, "companies": companies, "organizations": organizations,
            "memberships": memberships, "people": people, "contacts": contacts, "inactive_org": inactive_org}


def me_body(world, subject: str) -> dict:
    """`GET /me/operational-context` con esos datos: todas las membresías del `sub`, por `created_at`."""
    status_of = {row["id"]: row["status"] for row in world["companies"].values()}
    rows = sorted((row for row in world["memberships"] if row["keycloak_user_id"] == subject),
                  key=lambda row: (row["created_at"], str(row["id"])))
    return {"keycloak_user_id": subject, "memberships": [
        {"application_user_id": str(row["id"]), "company_id": str(row["company_id"]), "status": row["status"],
         "company_status": status_of[row["company_id"]], "company": None, "branches": []}
        for row in rows
    ]}


def visible_companies(world, subject: str, everyone: bool) -> set[UUID]:
    if everyone:
        return {row["id"] for row in world["companies"].values()}
    return {row["company_id"] for row in world["memberships"]
            if row["keycloak_user_id"] == subject and row["status"] == "ACTIVE"}


def oc_routes(world, subject: str, *, everyone: bool = False, companies_read: bool = True,
              memberships_read: bool = True) -> dict:
    """Respuestas de Operational Context para ese usuario según sus reglas de permiso y alcance."""
    routes = {("GET", "/api/v1/me/operational-context"): (200, me_body(world, subject)) if memberships_read
              else (403, {})}
    visible = visible_companies(world, subject, everyone)
    for row in world["companies"].values():
        path = f"/api/v1/companies/{row['id']}"
        if not companies_read:
            routes[("GET", path)] = (403, {})
        elif row["id"] in visible:
            routes[("GET", path)] = (200, {"id": str(row["id"]), "organization_identity_id":
                                           str(row["organization_identity_id"]), "status": row["status"]})
    return routes


def pi_routes(world, *, allowed: bool = True) -> dict:
    """Respuestas de Party Identity con esos datos (o `403` en todo si el token no tiene el permiso)."""
    routes = {}
    organizations = [*world["organizations"].values(), world["inactive_org"]]
    for row in organizations:
        routes[("GET", f"/api/v1/organization-identities/{row['id']}")] = (
            200, {"id": str(row["id"]), "legal_name": row["legal_name"], "status": row["status"]})
    for row in world["people"]:
        routes[("GET", f"/api/v1/person-identities/{row['id']}")] = (200, {"id": str(row["id"]), "status": row["status"]})
    for row in world["contacts"]:
        routes[("GET", f"/api/v1/organization-contact-persons/{row['id']}")] = (
            200, {"id": str(row["id"]), "organization_identity_id": str(row["organization_identity_id"]),
                  "is_active": row["is_active"]})
    if not allowed:
        routes = {key: (403, {}) for key in routes}
    return routes


# --------------------------------------------------------------------------- Operational Context: membresías


def test_member_companies_match_http(owners, world):
    reader = owners["oc"]["reader"]
    for subject in (world["sub"], world["other"], f"sin-membresias-{uuid4()}"):
        contract = ContractCompanyAccessDirectory(engine=reader, claims=claims(subject, MEMBERSHIPS_READ))
        double = http(HTTPCompanyAccessDirectory, oc_routes(world, subject))
        assert contract.list_member_companies() == double.list_member_companies(), subject

    companies = ContractCompanyAccessDirectory(engine=reader, claims=claims(world["sub"], MEMBERSHIPS_READ))
    listed = companies.list_member_companies()
    names = {row["id"]: name for name, row in world["companies"].items()}
    assert [names[item.company_id] for item in listed] == [
        names[company_id] for company_id in sorted({item.company_id for item in listed}, key=str)
    ]
    assert {names[item.company_id]: item.company_status for item in listed} == {
        "ACTIVA": "ACTIVE", "CERRADA": "INACTIVE", "REPETIDA": "ACTIVE", "SIN_RAZON_SOCIAL": "ACTIVE"}


def test_member_companies_without_permission_is_403(owners, world):
    contract = ContractCompanyAccessDirectory(engine=owners["oc"]["reader"], claims=claims(world["sub"], COMPANIES_READ))
    with pytest.raises(OperationalAccessDeniedError):
        contract.list_member_companies()
    with pytest.raises(OperationalAccessDeniedError):
        http(HTTPCompanyAccessDirectory, oc_routes(world, world["sub"], memberships_read=False)).list_member_companies()


# --------------------------------------------------------------------------- Operational Context: empresas


def _outcome(call, *args):
    try:
        return ("ok", call(*args))
    except (NotFoundError, OperationalAccessDeniedError) as error:
        return ("error", type(error))


@pytest.mark.parametrize(
    ("subject_key", "extra"),
    [("sub", ()), ("other", ()), ("sub", (PLATFORM_LOOKUP,)), ("other", (PLATFORM_ADMINISTER,))],
    ids=["miembro", "ajeno", "lookup", "administrador"],
)
def test_company_organization_matches_http(owners, world, subject_key, extra):
    subject = world[subject_key]
    contract = ContractCompanyDirectory(engine=owners["oc"]["reader"], claims=claims(subject, COMPANIES_READ, *extra))
    double = http(HTTPCompanyDirectory, oc_routes(world, subject, everyone=bool(extra)))
    ids = [row["id"] for row in world["companies"].values()] + [uuid4()]
    found = 0
    for company_id in ids:
        assert _outcome(contract.get_company_organization, company_id) == \
            _outcome(double.get_company_organization, company_id), company_id
        assert contract.find_company_organization(company_id) == double.find_company_organization(company_id)
        found += contract.find_company_organization(company_id) is not None
    assert found == len(visible_companies(world, subject, bool(extra)))
    assert contract.find_company_organizations(ids) == {company_id: double.find_company_organization(company_id)
                                                        for company_id in ids}


def test_company_without_permission_is_403(owners, world):
    contract = ContractCompanyDirectory(engine=owners["oc"]["reader"], claims=claims(world["sub"], MEMBERSHIPS_READ))
    double = http(HTTPCompanyDirectory, oc_routes(world, world["sub"], companies_read=False))
    company_id = world["companies"]["ACTIVA"]["id"]
    for directory in (contract, double):
        with pytest.raises(OperationalAccessDeniedError):
            directory.get_company_organization(company_id)
        assert directory.find_company_organization(company_id) is None
    assert contract.find_company_organizations([company_id]) == {company_id: None}


def test_company_batch_in_chunks_of_100_with_repeated_ids(owners, world):
    contract = ContractCompanyDirectory(engine=owners["oc"]["reader"],
                                        claims=claims(world["sub"], COMPANIES_READ, PLATFORM_LOOKUP))
    known = world["companies"]["REPETIDA"]
    ids = [uuid4() for _ in range(230)] + [known["id"], known["id"]]
    result = contract.find_company_organizations(ids)
    assert list(result) == list(dict.fromkeys(ids))
    assert {key: value for key, value in result.items() if value is not None} == {
        known["id"]: known["organization_identity_id"]}


# --------------------------------------------------------------------------- Party Identity


def test_party_directory_matches_http(owners, world):
    contract = ContractPartyDirectory(engine=owners["pi"]["reader"], claims=claims(world["sub"], *OWNER_READS))
    double = http(HTTPPartyDirectory, pi_routes(world))
    for row in world["people"]:
        assert contract.get_person(row["id"]) == double.get_person(row["id"])
    organizations = [*world["organizations"].values(), world["inactive_org"]]
    for row in organizations:
        assert contract.get_organization(row["id"]) == double.get_organization(row["id"])
        assert contract.find_organization_name(row["id"]) == double.find_organization_name(row["id"]) == \
            row["legal_name"]
    for row in world["contacts"]:
        assert contract.get_contact_person(row["id"]) == double.get_contact_person(row["id"])
    assert {contract.get_contact_person(row["id"]).is_active for row in world["contacts"]} == {True, False}
    assert {contract.get_person(row["id"]).status for row in world["people"]} == {"ACTIVE", "INACTIVE"}

    missing = uuid4()
    for method in ("get_person", "get_organization", "get_contact_person", "find_organization_name"):
        assert getattr(contract, method)(missing) is None
        assert getattr(double, method)(missing) is None

    ids = [row["id"] for row in organizations] + [missing, organizations[0]["id"]] + [uuid4() for _ in range(150)]
    assert contract.find_organization_names(ids) == {identity: double.find_organization_name(identity)
                                                     for identity in ids}


def test_party_directory_without_permission_is_403(owners, world):
    contract = ContractPartyDirectory(engine=owners["pi"]["reader"], claims=claims(world["sub"], MEMBERSHIPS_READ))
    double = http(HTTPPartyDirectory, pi_routes(world, allowed=False))
    person, contact = world["people"][0]["id"], world["contacts"][0]["id"]
    organization = world["organizations"]["ACTIVA"]["id"]
    for directory in (contract, double):
        for method, identity in (("get_person", person), ("get_organization", organization),
                                 ("get_contact_person", contact)):
            with pytest.raises(PartyIdentityAccessDeniedError):
                getattr(directory, method)(identity)
        assert directory.find_organization_name(organization) is None
    assert contract.find_organization_names([organization]) == {organization: None}

    # Cada método exige solo el permiso de su ruta.
    only_people = ContractPartyDirectory(engine=owners["pi"]["reader"], claims=claims(world["sub"], PERSONS_READ))
    assert only_people.get_person(person) is not None
    with pytest.raises(PartyIdentityAccessDeniedError):
        only_people.get_contact_person(contact)


# --------------------------------------------------------------------------- base detenida


def test_database_down_is_unavailable(world):
    oc = create_contract_engine(down_settings("oc"), application_name="cr-t062")
    pi = create_contract_engine(down_settings("pi"), application_name="cr-t062")
    roles = (*OWNER_READS, PLATFORM_LOOKUP)
    company_id = world["companies"]["ACTIVA"]["id"]
    organization = world["organizations"]["ACTIVA"]["id"]
    try:
        calls = [
            ("operational-context", lambda: ContractCompanyAccessDirectory(
                engine=oc, claims=claims(world["sub"], *roles)).list_member_companies()),
            ("operational-context", lambda: ContractCompanyDirectory(
                engine=oc, claims=claims(world["sub"], *roles)).get_company_organization(company_id)),
            ("operational-context", lambda: ContractCompanyDirectory(
                engine=oc, claims=claims(world["sub"], *roles)).find_company_organizations([company_id])),
            ("party-identity", lambda: ContractPartyDirectory(
                engine=pi, claims=claims(world["sub"], *roles)).find_organization_name(organization)),
            ("party-identity", lambda: ContractPartyDirectory(
                engine=pi, claims=claims(world["sub"], *roles)).get_contact_person(uuid4())),
        ]
        for provider, call in calls:
            with pytest.raises(DependencyUnavailableError) as info:
                call()
            assert info.value.provider == provider
            assert info.value.cause.startswith("contract:")
    finally:
        oc.dispose()
        pi.dispose()


# --------------------------------------------------------------------------- GET /company-summaries


SUMMARIES = "/api/v1/company-summaries"


@pytest.fixture
def outgoing(monkeypatch):
    """Solicitudes HTTP reales salientes (el `TestClient` no usa `HTTPTransport`)."""
    calls = []
    original = httpx.HTTPTransport.handle_request

    def counting(self, request):
        calls.append(str(request.url))
        return original(self, request)

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", counting)
    return calls


def http_app(test_settings, test_auth, world, subject: str, calls: list, *, memberships_read: bool = True):
    oc = oc_routes(world, subject, memberships_read=memberships_read)
    pi = pi_routes(world)

    def directory(cls, routes, request):
        return cls(base_url="http://owner.test/api/v1", authorization=request.headers.get("authorization"),
                   timeout_seconds=1, transport=routed(routes, calls))

    return create_app(
        test_settings, auth=test_auth,
        access_directory_factory=lambda request: directory(HTTPCompanyAccessDirectory, oc, request),
        company_directory_factory=lambda request: directory(HTTPCompanyDirectory, oc, request),
        party_directory_factory=lambda request: directory(HTTPPartyDirectory, pi, request),
    )


def contract_app(test_settings, test_auth, oc: ContractReadSettings, pi: ContractReadSettings):
    return create_app(
        dataclasses.replace(test_settings, operational_context_reads=oc, party_identity_reads=pi), auth=test_auth
    )


def _get(app, token: str, **params):
    with TestClient(app, raise_server_exceptions=False) as client:
        return client.get(SUMMARIES, params=params, headers={"Authorization": f"Bearer {token}"})


def _comparable(response) -> tuple[int, dict]:
    body = response.json()
    body.pop("trace_id", None)
    body.pop("instance", None)
    return response.status_code, body


def test_summaries_match_http_without_requests(owners, world, test_settings, test_auth, make_token, clean_database,
                                               outgoing):
    token = make_token(PRODUCTS_READ, *OWNER_READS, sub=world["sub"])
    http_calls: list = []
    via_http = http_app(test_settings, test_auth, world, world["sub"], http_calls)
    via_contract = contract_app(test_settings, test_auth, owners["oc"]["settings"], owners["pi"]["settings"])

    for params in ({"page_size": 100}, {"page_size": 1, "page": 2}, {"page_size": 3, "page": 2}, {"page": 9}, {}):
        expected = _get(via_http, token, **params)
        before = len(http_calls)
        actual = _get(via_contract, token, **params)
        assert expected.status_code == 200, expected.text
        assert actual.json() == expected.json(), params
        assert len(http_calls) == before  # el adaptador de contrato no llama a los dobles
    assert http_calls  # la vía HTTP sí consulta a los propietarios
    assert outgoing == []

    items = _get(via_contract, token, page_size=100).json()["items"]
    names = {str(row["id"]): name for name, row in world["companies"].items()}
    assert [names[item["company_id"]] for item in items] == [
        names[key] for key in sorted(item["company_id"] for item in items)]
    by_name = {names[item["company_id"]]: item for item in items}
    assert set(by_name) == {"ACTIVA", "CERRADA", "REPETIDA", "SIN_RAZON_SOCIAL"}
    assert by_name["SIN_RAZON_SOCIAL"]["legal_name"] is None
    assert by_name["REPETIDA"]["legal_name"] == world["organizations"]["REPETIDA"]["legal_name"]
    assert by_name["CERRADA"]["company_status"] == "INACTIVE"


def test_summaries_without_permission_is_same_403(owners, world, test_settings, test_auth, make_token, clean_database,
                                                  outgoing):
    token = make_token(PRODUCTS_READ, COMPANIES_READ, ORGANIZATIONS_READ, sub=world["sub"])
    expected = _get(http_app(test_settings, test_auth, world, world["sub"], [], memberships_read=False), token)
    actual = _get(contract_app(test_settings, test_auth, owners["oc"]["settings"], owners["pi"]["settings"]), token)
    assert expected.status_code == 403
    assert expected.json()["code"] == "COMMERCIAL_RELATIONSHIP.OPERATIONAL_ACCESS_DENIED"
    assert _comparable(actual) == _comparable(expected)
    assert outgoing == []


def test_summaries_without_name_permissions_match_http(owners, world, test_settings, test_auth, make_token,
                                                       clean_database, outgoing):
    """Sin `companies:read` ni `organization_identities:read` la razón social sale `null`, como con el `403` de hoy."""
    token = make_token(PRODUCTS_READ, MEMBERSHIPS_READ, sub=world["sub"])
    oc = oc_routes(world, world["sub"], companies_read=False)
    pi = pi_routes(world, allowed=False)

    def directory(cls, routes):
        return lambda request: cls(base_url="http://owner.test/api/v1", authorization="Bearer x", timeout_seconds=1,
                                   transport=routed(routes))

    via_http = create_app(test_settings, auth=test_auth,
                          access_directory_factory=directory(HTTPCompanyAccessDirectory, oc),
                          company_directory_factory=directory(HTTPCompanyDirectory, oc),
                          party_directory_factory=directory(HTTPPartyDirectory, pi))
    expected = _get(via_http, token, page_size=100)
    actual = _get(contract_app(test_settings, test_auth, owners["oc"]["settings"], owners["pi"]["settings"]), token,
                  page_size=100)
    assert expected.status_code == 200, expected.text
    assert actual.json() == expected.json()
    assert {item["legal_name"] for item in actual.json()["items"]} == {None}
    assert outgoing == []


@pytest.mark.parametrize("down", ["oc", "pi"])
def test_summaries_database_down_is_same_503(owners, world, test_settings, test_auth, make_token, clean_database,
                                             outgoing, down):
    token = make_token(PRODUCTS_READ, *OWNER_READS, sub=world["sub"])
    settings = {key: down_settings(key) if key == down else owners[key]["settings"] for key in OWNERS}
    actual = _get(contract_app(test_settings, test_auth, settings["oc"], settings["pi"]), token, page_size=100)

    # Hoy: Operational Context caído falla en `/me`; Party Identity caído falla en la primera razón social.
    oc = oc_routes(world, world["sub"])
    pi = pi_routes(world)

    def directory(cls, routes, is_down):
        def factory(request):
            transport = (httpx.MockTransport(lambda r: httpx.Response(503, json={})) if is_down
                         else routed(routes))
            return cls(base_url="http://owner.test/api/v1", authorization="Bearer x", timeout_seconds=1,
                       transport=transport)
        return factory

    via_http = create_app(test_settings, auth=test_auth,
                          access_directory_factory=directory(HTTPCompanyAccessDirectory, oc, down == "oc"),
                          company_directory_factory=directory(HTTPCompanyDirectory, oc, down == "oc"),
                          party_directory_factory=directory(HTTPPartyDirectory, pi, down == "pi"))
    expected = _get(via_http, token, page_size=100)
    assert expected.status_code == 503
    assert expected.json()["dependency"] == {"oc": "operational-context", "pi": "party-identity"}[down]
    assert _comparable(actual) == _comparable(expected)
    assert outgoing == []
