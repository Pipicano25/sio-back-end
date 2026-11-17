"""Adaptadores de contrato de Inventory frente a sus adaptadores HTTP con los mismos datos (spec 025, T066).

Crea en el contenedor de pruebas de Inventory las bases ``inventory_test__oc_dir`` e ``inventory_test__cr`` con las
migraciones reales de Operational Context y Commercial Relationship, el rol ``inv_contract_reader`` con su
``contract/grants.yaml``, y comprueba para cada método:

- mismo resultado que el adaptador HTTP cuando el propietario responde lo que respondería con esos datos;
- "no encontrado" igual que el ``404`` (o ``found=false``) de hoy;
- datos que hoy el adaptador HTTP rechaza como cuerpo inesperado (moneda inválida) → la misma indisponibilidad;
- base detenida → la misma ``DependencyUnavailableError(<proveedor>)`` que hoy produce el ``503``.
"""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sio_contract_read.testing_oc import seed_access_world
from sqlalchemy import create_engine, text

from inventory_service.application.exceptions import DependencyUnavailableError
from inventory_service.infrastructure.commercial_relationship_directory import HTTPCompanyProductDirectory
from inventory_service.infrastructure.contract_commercial_relationship import ContractCompanyProductDirectory
from inventory_service.infrastructure.contract_operational_context import ContractOperationalContextDirectory
from inventory_service.infrastructure.operational_context_directory import HTTPOperationalContextDirectory

SERVICES = Path(__file__).resolve().parents[3]
OWNERS = {"oc": "operational-context-service", "cr": "commercial-relationship-service"}
DATABASES = {"oc": "inventory_test__oc_dir", "cr": "inventory_test__cr"}
WHO = "prueba-spec-025"


class Tokens:
    def get_token(self) -> str:
        return "token-ficticio"

    def invalidate(self) -> None:
        return None


@pytest.fixture(scope="module")
def owners(test_database_url):
    result = {}
    # Los roles son del servidor: las dos bases comparten `inv_contract_reader` y su contraseña.
    password = secrets.token_urlsafe(24)
    for key, service in OWNERS.items():
        owner = SERVICES / service
        url = create_owner_schema(test_database_url, DATABASES[key], owner, recreate=True)
        reader_url = provision_reader(url, owner / "contract" / "grants.yaml", "inventory", password)
        settings = ContractReadSettings(prefix=key.upper(), source="contract", database_url=reader_url, timeout_seconds=2)
        result[key] = {"admin": create_engine(url), "reader": create_contract_engine(settings, application_name="t066")}
    yield result
    for item in result.values():
        item["admin"].dispose()
        item["reader"].dispose()


def routed(routes: dict):
    """Doble HTTP: `(método, ruta)` → `(estado, cuerpo)`; lo demás `404`."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        if key not in routes:
            return httpx.Response(404, json={})
        status, body = routes[key](request) if callable(routes[key]) else routes[key]
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def http(cls, routes: dict):
    return cls(base_url="http://owner.test/api/v1", timeout_seconds=2, tokens=Tokens(), transport=routed(routes))


def _json(value):
    return str(value) if isinstance(value, UUID) else value


# --------------------------------------------------------------------------- Operational Context


@pytest.fixture(scope="module")
def access(owners):
    cases = seed_access_world(owners["oc"]["admin"])
    case = next(case for case in cases if case.name == "permitido_sucursal")
    company_id, user_id = case.expected.company_id, case.expected.application_user_id
    with owners["oc"]["admin"].begin() as connection:
        connection.execute(text("UPDATE companies SET default_currency = 'COP' WHERE id = :i"), {"i": company_id})
        branch = connection.execute(
            text("SELECT b.company_id, b.status, c.status AS company_status FROM branches b"
                 " JOIN companies c ON c.id = b.company_id WHERE b.id = :i"), {"i": case.branch_id}
        ).mappings().one()
        user = connection.execute(text("SELECT company_id, status, keycloak_user_id FROM application_users WHERE id = :i"),
                                  {"i": user_id}).mappings().one()
    return {"company": company_id, "branch": case.branch_id, "user": user_id, "branch_row": dict(branch),
            "user_row": dict(user)}


def _oc_double(access, *, currency="COP"):
    company, branch, user = access["company"], access["branch"], access["user"]
    return http(HTTPOperationalContextDirectory, {
        ("GET", f"/api/v1/companies/{company}"): (200, {"id": str(company), "default_currency": currency}),
        ("GET", f"/api/v1/branches/{branch}"): (200, {"id": str(branch), **{k: _json(v) for k, v in access["branch_row"].items()}}),
        ("GET", f"/api/v1/application-users/{user}"): (200, {"id": str(user), **{k: _json(v) for k, v in access["user_row"].items()}}),
    })


def test_operational_context_directory_matches_http(owners, access):
    contract = ContractOperationalContextDirectory(engine=owners["oc"]["reader"])
    double = _oc_double(access)
    assert contract.get_branch(access["branch"]) == double.get_branch(access["branch"])
    assert contract.get_application_user(access["user"]) == double.get_application_user(access["user"])
    assert contract.get_company_currency(access["company"]) == double.get_company_currency(access["company"]) == "COP"
    missing = uuid4()
    assert contract.get_branch(missing) is None
    assert contract.get_application_user(missing) is None
    assert contract.get_company_currency(missing) is None


def test_branch_of_inactive_company_keeps_company_status(owners, access):
    """`company_status` sale de la empresa, igual que `GET /branches/{id}`."""
    company = uuid4()
    with owners["oc"]["admin"].begin() as connection:
        connection.execute(text("INSERT INTO companies (id, organization_identity_id, status, version, created_by, updated_by)"
                                " VALUES (:id, :org, 'INACTIVE', 1, :who, :who)"), {"id": company, "org": uuid4(), "who": WHO})
        branch = uuid4()
        connection.execute(text("INSERT INTO branches (id, company_id, code, name, status, version, created_by, updated_by)"
                                " VALUES (:id, :c, 'INV1', 'Sucursal ficticia', 'ACTIVE', 1, :who, :who)"),
                           {"id": branch, "c": company, "who": WHO})
    found = ContractOperationalContextDirectory(engine=owners["oc"]["reader"]).get_branch(branch)
    assert (found.company_id, found.status, found.company_status) == (company, "ACTIVE", "INACTIVE")


def test_non_uuid_keycloak_subject_is_none_like_http(owners, access):
    """Hoy `keycloak_user_id` que no es UUID queda en `None`: la vista conserva la misma lectura."""
    user_id = uuid4()
    with owners["oc"]["admin"].begin() as connection:
        connection.execute(text("INSERT INTO application_users (id, company_id, keycloak_user_id, person_identity_id,"
                                " display_name, status, created_by, updated_by) VALUES (:id, :c, 'sub-no-uuid', :p,"
                                " 'Ficticio', 'ACTIVE', :who, :who)"),
                           {"id": user_id, "c": access["company"], "p": uuid4(), "who": WHO})
    found = ContractOperationalContextDirectory(engine=owners["oc"]["reader"]).get_application_user(user_id)
    assert found.keycloak_user_id is None and found.company_id == access["company"]


def test_invalid_currency_is_unavailable_like_http(owners, access):
    company = uuid4()
    with owners["oc"]["admin"].begin() as connection:
        connection.execute(text("INSERT INTO companies (id, organization_identity_id, status, version, created_by, updated_by)"
                                " VALUES (:id, :org, 'ACTIVE', 1, :who, :who)"), {"id": company, "org": uuid4(), "who": WHO})
        current = connection.execute(text("SELECT default_currency FROM companies WHERE id = :i"), {"i": company}).scalar()
    contract = ContractOperationalContextDirectory(engine=owners["oc"]["reader"])
    double = _oc_double({**access, "company": company}, currency=current)
    if current is not None and len(current) == 3 and current.isupper():
        assert contract.get_company_currency(company) == double.get_company_currency(company)
        return
    with pytest.raises(DependencyUnavailableError) as expected:
        double.get_company_currency(company)
    with pytest.raises(DependencyUnavailableError) as info:
        contract.get_company_currency(company)
    assert info.value.provider == expected.value.provider == "operational-context"


# --------------------------------------------------------------------------- Commercial Relationship


@pytest.fixture(scope="module")
def products(owners):
    company, other = uuid4(), uuid4()
    rows = []
    for index, (owner_company, status, control) in enumerate(
        ((company, "ACTIVE", True), (company, "INACTIVE", True), (company, "ACTIVE", False), (other, "ACTIVE", True))
    ):
        row = {"id": uuid4(), "company_id": owner_company, "global_product_id": uuid4(),
               "internal_code": f"I-{index}-{uuid4().hex[:6]}", "display_name": f"Producto ficticio {index}",
               "currency_code": "COP", "status": status, "inventory_control_enabled": control,
               "created_by": WHO, "updated_by": WHO}
        with owners["cr"]["admin"].begin() as connection:
            connection.execute(text(f"INSERT INTO company_products ({', '.join(row)}) VALUES ({', '.join(':' + k for k in row)})"), row)
        rows.append(row)
    return rows


def _batch(rows):
    by_id = {str(row["id"]): row for row in rows}

    def handler(request: httpx.Request):
        items = []
        for value in json.loads(request.content)["ids"]:
            row = by_id.get(value)
            items.append({"id": value, "found": False} if row is None else {
                "found": True, "id": value, "company_id": str(row["company_id"]), "status": row["status"],
                "inventory_control_enabled": row["inventory_control_enabled"]})
        return 200, {"items": items}

    return handler


def test_company_products_match_http(owners, products):
    contract = ContractCompanyProductDirectory(engine=owners["cr"]["reader"])
    double = http(HTTPCompanyProductDirectory, {("POST", "/api/v1/company-products/batch-lookup"): _batch(products)})
    ids = [row["id"] for row in products] + [uuid4()]
    assert contract.lookup(ids) == double.lookup(ids)
    assert len(contract.lookup(ids)) == len(products)
    assert contract.lookup([]) == {} == double.lookup([])


def test_company_products_in_batches_of_100(owners, products):
    contract = ContractCompanyProductDirectory(engine=owners["cr"]["reader"])
    many = [uuid4() for _ in range(230)] + [products[0]["id"], products[0]["id"]]
    assert list(contract.lookup(many)) == [products[0]["id"]]


# --------------------------------------------------------------------------- base detenida


def down_engine(key: str):
    settings = ContractReadSettings(
        prefix=key.upper(), source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url=f"postgresql+psycopg://inv_contract_reader:x@127.0.0.1:1/{DATABASES[key]}",
    )
    return create_contract_engine(settings, application_name="t066")


@pytest.mark.parametrize(
    ("key", "call", "provider"),
    [
        ("oc", lambda engine: ContractOperationalContextDirectory(engine=engine).get_branch(uuid4()), "operational-context"),
        ("oc", lambda engine: ContractOperationalContextDirectory(engine=engine).get_application_user(uuid4()),
         "operational-context"),
        ("oc", lambda engine: ContractOperationalContextDirectory(engine=engine).get_company_currency(uuid4()),
         "operational-context"),
        ("cr", lambda engine: ContractCompanyProductDirectory(engine=engine).lookup([uuid4()]), "commercial-relationship"),
    ],
)
def test_database_down_is_unavailable(key, call, provider):
    engine = down_engine(key)
    try:
        with pytest.raises(DependencyUnavailableError) as info:
            call(engine)
        assert info.value.provider == provider
        assert info.value.cause.startswith("contract:")
    finally:
        engine.dispose()
