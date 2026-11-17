"""Adaptadores de contrato de Business Reporting frente a sus adaptadores HTTP con los mismos datos (spec 025, T074).

Crea en el servidor de pruebas (ver `conftest.py`) las bases `business_reporting_test__oc_dir` y
`business_reporting_test__pc` con las migraciones reales de Operational Context y Product Catalog, y el rol
`brs_contract_reader` con sus `contract/grants.yaml`. Para `company`, `branches` y `base_units` comprueba:

- mismo resultado que el adaptador HTTP cuando el propietario responde lo que respondería con esos datos (incluida la
  visibilidad por membresía `ACTIVE`, `platform:administer` y `platform:lookup` de Operational Context);
- "no encontrado" o fuera del alcance igual que el `404` (o `found=false`) de hoy;
- sin el permiso de la ruta del propietario, lo mismo que hoy produce su `403` (FR-037);
- base detenida → la misma `DependencyUnavailableError(<proveedor>, <operación>)` que hoy produce el `503`, con causa
  `contract:`.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sqlalchemy import create_engine, text

from business_reporting_service.application.exceptions import DependencyUnavailableError, OwnerForbiddenError
from business_reporting_service.config import Settings
from business_reporting_service.api.dependencies import build_http_dependencies
from business_reporting_service.infrastructure.catalog import HTTPProductCatalog
from business_reporting_service.infrastructure.contract_operational_context import ContractOperationalContext
from business_reporting_service.infrastructure.contract_product_catalog import ContractProductCatalog
from business_reporting_service.infrastructure.http_client import AsyncDependencyClient, UserCaller
from business_reporting_service.infrastructure.operational_context import HTTPOperationalContext
from tests.contract_reads.conftest import SERVICES, claims

OWNERS = {"oc": SERVICES / "operational-context-service", "pc": SERVICES / "product-catalog-service"}
DATABASES = {"oc": "business_reporting_test__oc_dir", "pc": "business_reporting_test__pc"}
PREFIX = {"oc": "OPERATIONAL_CONTEXT", "pc": "PRODUCT_CATALOG"}
WHO = "prueba-spec-025"

COMPANIES_READ = "perm:operational-context:companies:read"
BRANCHES_READ = "perm:operational-context:branches:read"
ADMINISTER = "perm:operational-context:platform:administer"
LOOKUP = "perm:operational-context:platform:lookup"
PRODUCTS_READ = "perm:product-catalog:products:read"
OC_READ = (COMPANIES_READ, BRANCHES_READ)


@pytest.fixture(scope="module")
def owners(contract_admin_url, reader_password):
    result = {}
    for key, owner in OWNERS.items():
        url = create_owner_schema(contract_admin_url, DATABASES[key], owner, recreate=True)
        reader_url = provision_reader(url, owner / "contract" / "grants.yaml", "business-reporting", reader_password)
        settings = ContractReadSettings(prefix=PREFIX[key], source="contract", database_url=reader_url,
                                        timeout_seconds=2)
        result[key] = {"admin": create_engine(url), "reader": create_contract_engine(settings, application_name="t074")}
    yield result
    for item in result.values():
        item["admin"].dispose()
        item["reader"].dispose()


def insert(owners, key: str, table: str, **values) -> dict:
    columns = ", ".join(values)
    marks = ", ".join(f":{name}" for name in values)
    with owners[key]["admin"].begin() as connection:
        connection.execute(text(f"INSERT INTO public.{table} ({columns}) VALUES ({marks})"), values)
    return values


def audit() -> dict:
    return {"created_by": WHO, "updated_by": WHO}


def down_engine(key: str):
    settings = ContractReadSettings(
        prefix=PREFIX[key], source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url=f"postgresql+psycopg://brs_contract_reader:x@127.0.0.1:1/{DATABASES[key]}",
    )
    return create_contract_engine(settings, application_name="t074")


def client(provider: str, handler) -> AsyncDependencyClient:
    return AsyncDependencyClient(provider=provider, base_url="http://owner.test/api/v1", timeout_seconds=2,
                                 transport=httpx.MockTransport(handler))


def run(coroutine):
    return asyncio.run(coroutine)


# --------------------------------------------------------------------------- Operational Context


class OCWorld:
    """Empresas, sucursales y membresías; `respond` es lo que respondería Operational Context con estos datos."""

    def __init__(self, owners) -> None:
        start = datetime.now(UTC) - timedelta(days=1)
        self.c = self._company(owners, "America/Bogota", "COP")
        self.d = self._company(owners, "America/Lima", "PEN")
        # Orden de creación distinto del orden de código: el propietario ordena por `created_at` e `id`.
        self.branches = {
            "Z": self._branch(owners, self.c, "Z9", "ACTIVE", None, start),
            "A": self._branch(owners, self.c, "A1", "ACTIVE", "America/Lima", start + timedelta(minutes=1)),
            "M": self._branch(owners, self.c, "M5", "ACTIVE", None, start + timedelta(minutes=2)),
            "I": self._branch(owners, self.c, "I1", "INACTIVE", None, start + timedelta(minutes=3)),
            "D": self._branch(owners, self.d, "D1", "ACTIVE", None, start),
        }
        self.member, self.inactive, self.outsider, self.two = (f"sub-{n}-{uuid4()}" for n in ("m", "i", "o", "dos"))
        self.admin, self.lookup = f"sub-admin-{uuid4()}", f"sub-lookup-{uuid4()}"
        self._member(owners, self.c, self.member, "ACTIVE")
        self._member(owners, self.c, self.inactive, "INACTIVE")
        self._member(owners, self.d, self.outsider, "ACTIVE")
        # Una membresía inactiva más reciente que la activa: sigue siendo miembro `ACTIVE`.
        self._member(owners, self.c, self.two, "ACTIVE", age_days=5)
        self._member(owners, self.c, self.two, "INACTIVE", age_days=1)
        self.memberships = {self.member: {self.c}, self.outsider: {self.d}, self.two: {self.c}}
        self.companies = {self.c: ("America/Bogota", "COP"), self.d: ("America/Lima", "PEN")}

    @staticmethod
    def _company(owners, timezone: str, currency: str) -> UUID:
        return insert(owners, "oc", "companies", id=uuid4(), organization_identity_id=uuid4(), status="ACTIVE",
                      timezone=timezone, default_currency=currency, version=1, **audit())["id"]

    @staticmethod
    def _branch(owners, company_id, code, status, timezone, created_at) -> dict:
        return insert(owners, "oc", "branches", id=uuid4(), company_id=company_id, code=code, name=f"Sucursal {code}",
                      status=status, timezone=timezone, version=1, created_at=created_at, **audit())

    @staticmethod
    def _member(owners, company_id, subject, status, age_days: int = 0) -> None:
        insert(owners, "oc", "application_users", id=uuid4(), company_id=company_id, keycloak_user_id=subject,
               person_identity_id=uuid4(), display_name="Ficticio", status=status,
               updated_at=datetime.now(UTC) - timedelta(days=age_days), **audit())

    def _visible(self, subject: str, roles: tuple, company_id: UUID, *, lookup_read: bool) -> bool:
        if ADMINISTER in roles or company_id in self.memberships.get(subject, set()):
            return True
        return lookup_read and LOOKUP in roles

    def respond(self, subject: str, roles: tuple):
        def handler(request: httpx.Request) -> httpx.Response:
            parts = request.url.path.removeprefix("/api/v1/").split("/")
            company_id = UUID(parts[1])
            exists = company_id in self.companies
            if len(parts) == 2:
                if COMPANIES_READ not in roles:
                    return httpx.Response(403, json={})
                if not exists or not self._visible(subject, roles, company_id, lookup_read=True):
                    return httpx.Response(404, json={})
                timezone, currency = self.companies[company_id]
                return httpx.Response(200, json={"id": str(company_id), "status": "ACTIVE", "timezone": timezone,
                                                 "default_currency": currency})
            if BRANCHES_READ not in roles:
                return httpx.Response(403, json={})
            if not exists or not self._visible(subject, roles, company_id, lookup_read=False):
                return httpx.Response(404, json={})
            status = request.url.params["status"]
            rows = sorted((b for b in self.branches.values() if b["company_id"] == company_id and b["status"] == status),
                          key=lambda b: (b["created_at"], str(b["id"])))
            timezone = self.companies[company_id][0]
            items = [{"id": str(b["id"]), "company_id": str(company_id), "code": b["code"], "name": b["name"],
                      "status": b["status"], "effective_timezone": b["timezone"] or timezone} for b in rows]
            return httpx.Response(200, json={"items": items, "page": 1, "page_size": 100,
                                             "total_records": len(items), "total_pages": 1})

        return handler


@pytest.fixture(scope="module")
def oc_world(owners):
    return OCWorld(owners)


def oc_pair(owners, world: OCWorld, subject: str, roles: tuple):
    http = HTTPOperationalContext(client("operational-context", world.respond(subject, roles)), "Bearer x")
    contract = ContractOperationalContext(engine=owners["oc"]["reader"], claims=claims(subject, *roles))
    return http, contract


def oc_cases(world: OCWorld):
    unknown = uuid4()
    return [
        ("miembro", world.member, OC_READ, world.c),
        ("miembro_otra_empresa", world.member, OC_READ, world.d),
        ("membresia_inactiva", world.inactive, OC_READ, world.c),
        ("ajeno", world.outsider, OC_READ, world.c),
        ("ajeno_su_empresa", world.outsider, OC_READ, world.d),
        ("activa_y_luego_inactiva", world.two, OC_READ, world.c),
        ("administrador", world.admin, (*OC_READ, ADMINISTER), world.c),
        ("lookup", world.lookup, (*OC_READ, LOOKUP), world.c),
        ("sin_membresia", world.lookup, OC_READ, world.c),
        ("empresa_inexistente", world.member, OC_READ, unknown),
        ("administrador_inexistente", world.admin, (*OC_READ, ADMINISTER), unknown),
        ("sin_permiso_de_empresa", world.member, (BRANCHES_READ,), world.c),
        ("sin_permiso_de_sucursales", world.member, (COMPANIES_READ,), world.c),
        ("sin_permisos", world.member, ("perm:business-reporting:all:read",), world.c),
    ]


def test_company_matches_http_adapter(owners, oc_world):
    seen = set()
    for name, subject, roles, company_id in oc_cases(oc_world):
        http, contract = oc_pair(owners, oc_world, subject, roles)
        expected = run(http.company(company_id))
        assert run(contract.company(company_id)) == expected, name
        seen.add(expected is None)
    assert seen == {True, False}


def test_branches_match_http_adapter_in_owner_order(owners, oc_world):
    seen = set()
    for name, subject, roles, company_id in oc_cases(oc_world):
        for status in ("ACTIVE", "INACTIVE"):
            http, contract = oc_pair(owners, oc_world, subject, roles)
            expected = run(http.branches(company_id, status=status))
            assert run(contract.branches(company_id, status=status)) == expected, (name, status)
            seen.add(len(expected))
    assert {0, 1, 3} <= seen
    _, contract = oc_pair(owners, oc_world, oc_world.member, OC_READ)
    active = run(contract.branches(oc_world.c, status="ACTIVE"))
    assert [b.code for b in active] == ["Z9", "A1", "M5"]
    assert [b.timezone for b in active] == ["America/Bogota", "America/Lima", "America/Bogota"]


def test_lookup_reads_the_company_but_not_its_branches(owners, oc_world):
    _, contract = oc_pair(owners, oc_world, oc_world.lookup, (*OC_READ, LOOKUP))
    assert run(contract.company(oc_world.c)) is not None
    assert run(contract.branches(oc_world.c, status="ACTIVE")) == []


def test_operational_context_down_is_unavailable(oc_world):
    engine = down_engine("oc")
    contract = ContractOperationalContext(engine=engine, claims=claims(oc_world.member, *OC_READ))

    def broken(request):
        raise httpx.ConnectError("caída")

    http = HTTPOperationalContext(client("operational-context", broken), "Bearer x")
    try:
        for call in (lambda port: port.company(oc_world.c), lambda port: port.branches(oc_world.c, status="ACTIVE")):
            with pytest.raises(DependencyUnavailableError) as today:
                run(call(http))
            with pytest.raises(DependencyUnavailableError) as info:
                run(call(contract))
            assert (info.value.provider, info.value.operation) == (today.value.provider, today.value.operation)
            assert info.value.cause.startswith("contract:")
    finally:
        engine.dispose()


# --------------------------------------------------------------------------- Product Catalog


@pytest.fixture(scope="module")
def catalog(owners):
    now = datetime.now(UTC)
    unit = insert(owners, "pc", "global_units_of_measure", id=uuid4(), code=f"U{uuid4().hex[:6].upper()}",
                  name="Unidad ficticia", symbol="u", measurement_type="UNIT", allows_decimals=False,
                  created_at=now, updated_at=now, **audit())
    products = {}
    for status in ("ACTIVE", "INACTIVE"):
        products[status] = insert(owners, "pc", "global_products", id=uuid4(), product_type="GOOD", status=status,
                                  canonical_name=f"PRODUCTO {status} {uuid4().hex[:6]}",
                                  canonical_name_key=uuid4().hex, base_unit_id=unit["id"], created_at=now,
                                  updated_at=now, **audit())
    return {"unit": unit, **products}


def pc_handler(catalog, *, status: int = 200, calls: list | None = None):
    """Lo que respondería `POST /products/summaries/batch-lookup` con estos datos (solo lo que lee BRS)."""
    products = {catalog[s]["id"]: catalog[s] for s in ("ACTIVE", "INACTIVE")}
    unit = catalog["unit"]

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        if status != 200:
            return httpx.Response(status, json={})
        items = []
        for raw in json.loads(request.content)["ids"]:
            product = products.get(UUID(raw))
            if product is None:
                items.append({"id": raw, "found": False})
                continue
            items.append({"id": raw, "found": True, "status": product["status"],
                          "base_unit": {"id": str(unit["id"]), "code": unit["code"], "name": unit["name"]}})
        return httpx.Response(200, json={"items": items})

    return handler


def pc_pair(owners, catalog, roles: tuple, **handler_options):
    http = HTTPProductCatalog(UserCaller(client("product-catalog", pc_handler(catalog, **handler_options)), "Bearer x"))
    contract = ContractProductCatalog(engine=owners["pc"]["reader"], claims=claims("sub-pc", *roles))
    return http, contract


def test_base_units_match_http_adapter(owners, catalog):
    unknown = uuid4()
    ids = [catalog["ACTIVE"]["id"], unknown, catalog["INACTIVE"]["id"], catalog["ACTIVE"]["id"]]
    http, contract = pc_pair(owners, catalog, (PRODUCTS_READ,))
    expected = run(http.base_units(ids))
    observed = run(contract.base_units(ids))
    assert observed == expected
    assert list(observed) == list(expected)
    assert observed[unknown] is None and observed[catalog["INACTIVE"]["id"]] is not None


def test_base_units_in_batches_of_100(owners, catalog):
    calls = []
    ids = [uuid4() for _ in range(150)] + [catalog["ACTIVE"]["id"]]
    http, contract = pc_pair(owners, catalog, (PRODUCTS_READ,), calls=calls)
    assert run(contract.base_units(ids)) == run(http.base_units(ids))
    assert len(calls) == 2


def test_base_units_without_permission_is_owner_forbidden(owners, catalog):
    ids = [catalog["ACTIVE"]["id"]]
    http, _ = pc_pair(owners, catalog, (), status=403)
    with pytest.raises(OwnerForbiddenError) as today:
        run(http.base_units(ids))
    _, contract = pc_pair(owners, catalog, ("perm:business-reporting:all:read",))
    with pytest.raises(OwnerForbiddenError) as info:
        run(contract.base_units(ids))
    assert (info.value.provider, info.value.operation) == (today.value.provider, today.value.operation)
    # Sin ids no hay llamada ni comprobación, como hoy.
    assert run(contract.base_units([])) == {} == run(http.base_units([]))


def test_product_catalog_down_is_unavailable(catalog):
    engine = down_engine("pc")
    contract = ContractProductCatalog(engine=engine, claims=claims("sub-pc", PRODUCTS_READ))

    def broken(request):
        raise httpx.ConnectError("caída")

    http = HTTPProductCatalog(UserCaller(client("product-catalog", broken), "Bearer x"))
    try:
        with pytest.raises(DependencyUnavailableError) as today:
            run(http.base_units([catalog["ACTIVE"]["id"]]))
        with pytest.raises(DependencyUnavailableError) as info:
            run(contract.base_units([catalog["ACTIVE"]["id"]]))
        assert (info.value.provider, info.value.operation) == (today.value.provider, today.value.operation)
        assert info.value.cause.startswith("contract:")
    finally:
        engine.dispose()


# --------------------------------------------------------------------------- selección por configuración


def _settings(oc_source: str, pc_source: str) -> Settings:
    def reads(prefix: str, source: str):
        url = None if source == "http" else f"postgresql+psycopg://brs_contract_reader:x@127.0.0.1:1/{prefix.lower()}"
        return ContractReadSettings(prefix=prefix, source=source, database_url=url, timeout_seconds=1)

    base = "http://owner.test/api/v1"
    return Settings(docs_enabled=False, operational_context_base_url=base, sales_base_url=base, purchase_base_url=base,
                    inventory_base_url=base, commercial_relationship_base_url=base, product_catalog_base_url=base,
                    operational_context_reads=reads("OPERATIONAL_CONTEXT", oc_source),
                    product_catalog_reads=reads("PRODUCT_CATALOG", pc_source))


def test_read_source_selects_adapters():
    for oc_source, pc_source in (("http", "http"), ("contract", "http"), ("http", "contract"), ("contract", "contract")):
        dependencies = build_http_dependencies(_settings(oc_source, pc_source))
        try:
            assert (dependencies.contract_oc is not None) == (oc_source == "contract")
            assert (dependencies.contract_pc is not None) == (pc_source == "contract")
            if dependencies.contract_oc is not None:
                assert isinstance(dependencies.contract_oc(None), ContractOperationalContext)
            if dependencies.contract_pc is not None:
                assert isinstance(dependencies.contract_pc(None), ContractProductCatalog)
        finally:
            run(dependencies.close())
