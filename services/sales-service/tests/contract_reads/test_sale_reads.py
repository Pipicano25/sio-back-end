"""Adaptadores de contrato de la venta frente a sus adaptadores HTTP con los mismos datos (spec 025, T048).

Crea en el contenedor de pruebas de Sales las bases ``sales_test__{pc,cr,pi,pr,inv,oc}`` con las migraciones reales
de cada propietario, el rol ``sal_contract_reader`` con su ``contract/grants.yaml``, y comprueba para cada método:

- mismo resultado que el adaptador HTTP cuando el propietario responde lo que respondería con esos datos;
- "no encontrado" igual que el ``404`` (o ``found=false``) de hoy;
- base detenida → la misma ``DependencyUnavailableError(<proveedor>)`` que hoy produce el ``503``.

Los datos son ficticios; los nombres solo usan mayúsculas ASCII para que el orden de PostgreSQL y el de Python
coincidan en la búsqueda de identidades.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sio_auth import TokenClaims
from sio_auth.permissions import extract_permission_grants
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sio_contract_read.testing_oc import seed_access_world
from sqlalchemy import create_engine, text

from sales_service.application.exceptions import DependencyUnavailableError
from sales_service.application.ports import ORGANIZATION, PERSON
from sales_service.infrastructure.commercial_relationship_directory import HTTPCommercialDirectory
from sales_service.infrastructure.contract_commercial_relationship import (
    ContractCommercialDirectory,
    ContractCustomerRegistry,
)
from sales_service.infrastructure.contract_inventory import ContractInventoryGateway
from sales_service.infrastructure.contract_operational_context import ContractOperationalContextDirectory
from sales_service.infrastructure.contract_party_identity import ContractPartyDirectory
from sales_service.infrastructure.contract_payment_reference import ContractPaymentReferenceDirectory
from sales_service.infrastructure.contract_product_catalog import ContractCatalogDirectory
from sales_service.infrastructure.customer_registry import HTTPCustomerRegistry
from sales_service.infrastructure.inventory_gateway import HTTPInventoryGateway
from sales_service.infrastructure.operational_context_directory import HTTPOperationalContextDirectory
from sales_service.infrastructure.party_identity_directory import HTTPPartyDirectory
from sales_service.infrastructure.payment_reference_directory import HTTPPaymentReferenceDirectory
from sales_service.infrastructure.product_catalog_directory import HTTPCatalogDirectory
from tests.contract.adapter_support import Tokens

SERVICES = Path(__file__).resolve().parents[3]
OWNERS = {
    "pc": "product-catalog-service",
    "cr": "commercial-relationship-service",
    "pi": "party-identity-service",
    "pr": "payment-reference-service",
    "inv": "inventory-service",
    "oc": "operational-context-service",
}
OWNER_ENV = {"PARTY_IDENTITY_SEED_COUNTRY_ID": "6f1c1b54-0d0e-4a63-9a8c-6f0f8f7f1a11"}
WHO = "prueba-spec-025"


# --------------------------------------------------------------------------- infraestructura


@pytest.fixture(scope="module")
def owners(test_database_url):
    """URL de administrador y motor de lectura de cada propietario."""
    result = {}
    # Los roles son del servidor: en este contenedor las seis bases comparten `sal_contract_reader` y su contraseña.
    password = secrets.token_urlsafe(24)
    for key, service in OWNERS.items():
        owner = SERVICES / service
        url = create_owner_schema(test_database_url, f"sales_test__{key}", owner, OWNER_ENV, recreate=True)
        reader_url = provision_reader(url, owner / "contract" / "grants.yaml", "sales", password)
        settings = ContractReadSettings(prefix=key.upper(), source="contract", database_url=reader_url, timeout_seconds=2)
        result[key] = {"admin": create_engine(url), "reader": create_contract_engine(settings, application_name="t048")}
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


def down_engine(key: str):
    settings = ContractReadSettings(
        prefix=key.upper(), source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url=f"postgresql+psycopg://sal_contract_reader:x@127.0.0.1:1/sales_test__{key}",
    )
    return create_contract_engine(settings, application_name="t048")


def routed(routes: dict):
    """Doble HTTP: `(método, ruta)` → `(estado, cuerpo)`; lo demás `404`."""

    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path)
        if key not in routes:
            return httpx.Response(404, json={})
        status, body = routes[key](request) if callable(routes[key]) else routes[key]
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def http(cls, routes: dict, base: str = "http://owner.test/api/v1"):
    return cls(base_url=base, timeout_seconds=2, tokens=Tokens(), transport=routed(routes))


def _json(value):
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def body(row: dict, *names: str) -> dict:
    return {name: _json(row[name]) for name in names}


def claims(subject: str, *roles: str) -> TokenClaims:
    return TokenClaims(
        subject=subject, issuer="test", audiences=("sio-api",), expires_at=datetime.now(UTC) + timedelta(minutes=5),
        roles=frozenset(roles), permissions=extract_permission_grants(roles), preferred_username=None, email=None,
        raw={},
    )


def audit() -> dict:
    return {"created_by": WHO, "updated_by": WHO}


# --------------------------------------------------------------------------- Product Catalog


@pytest.fixture(scope="module")
def catalog(owners):
    now = datetime.now(UTC)
    unit = insert(owners, "pc", "global_units_of_measure", id=uuid4(), code=f"U{secrets.token_hex(3).upper()}",
                  name="Unidad ficticia", symbol="u", measurement_type="UNIT", allows_decimals=False,
                  created_at=now, updated_at=now, **audit())
    rows = {}
    for status in ("ACTIVE", "INACTIVE"):
        product = insert(owners, "pc", "global_products", id=uuid4(), product_type="GOOD", status=status,
                         canonical_name=f"PRODUCTO {status} {uuid4().hex[:6]}", canonical_name_key=uuid4().hex,
                         base_unit_id=unit["id"], created_at=now, updated_at=now, **audit())
        presentation = insert(owners, "pc", "global_product_presentations", id=uuid4(), global_product_id=product["id"],
                              code=f"CJ{secrets.token_hex(2).upper()}", name="Caja x 12", is_base=False,
                              base_quantity=Decimal("12.0000"), status=status, created_at=now, updated_at=now,
                              **audit())
        rows[status] = {"product": product, "presentation": presentation}
    return {"unit": unit, **rows}


def test_catalog_matches_http(owners, catalog):
    contract = ContractCatalogDirectory(engine=owners["pc"]["reader"])
    for status in ("ACTIVE", "INACTIVE"):
        product, presentation = catalog[status]["product"], catalog[status]["presentation"]
        double = http(HTTPCatalogDirectory, {
            ("GET", f"/api/v1/presentations/{presentation['id']}"): (200, body(presentation, "id", "code", "name", "base_quantity", "status")),
            ("GET", f"/api/v1/products/{product['id']}"): (200, body(product, "id", "base_unit_id", "status")),
            ("GET", f"/api/v1/units-of-measure/{catalog['unit']['id']}"): (200, body(catalog["unit"], "id", "code")),
        })
        assert contract.get_presentation(presentation["id"]) == double.get_presentation(presentation["id"])
        assert contract.get_product(product["id"]) == double.get_product(product["id"])
        assert contract.get_unit(catalog["unit"]["id"]) == double.get_unit(catalog["unit"]["id"])
    missing = uuid4()
    assert contract.get_presentation(missing) is None
    assert contract.get_product(missing) is None
    assert contract.get_unit(missing) is None


# --------------------------------------------------------------------------- Payment Reference


def test_payment_method_matches_http(owners):
    now = datetime.now(UTC)
    contract = ContractPaymentReferenceDirectory(engine=owners["pr"]["reader"])
    for status in ("ACTIVE", "INACTIVE"):
        method = insert(owners, "pr", "global_payment_methods", id=uuid4(), code=f"M{secrets.token_hex(3).upper()}",
                        name=f"Medio ficticio {status}", method_type="CASH", status=status, created_at=now,
                        updated_at=now, **audit())
        double = http(HTTPPaymentReferenceDirectory, {
            ("GET", f"/global-payment-methods/{method['id']}"): (200, body(method, "id", "code", "name", "status"))},
            base="http://owner.test")
        assert contract.get_payment_method(method["id"]) == double.get_payment_method(method["id"])
    assert contract.get_payment_method(uuid4()) is None


# --------------------------------------------------------------------------- Commercial Relationship


@pytest.fixture(scope="module")
def commercial(owners):
    company, other = uuid4(), uuid4()
    products, presentations = [], []
    for index, (owner_company, status) in enumerate(((company, "ACTIVE"), (company, "INACTIVE"), (other, "ACTIVE"))):
        product = insert(owners, "cr", "company_products", id=uuid4(), company_id=owner_company, global_product_id=uuid4(),
                         internal_code=f"P-{index}-{uuid4().hex[:6]}", display_name=f"Producto ficticio {index}",
                         currency_code="COP", status=status, is_sellable=index != 1, inventory_control_enabled=index == 0,
                         **audit())
        presentation = insert(owners, "cr", "company_product_presentations", id=uuid4(), company_id=owner_company,
                              company_product_id=product["id"], global_product_presentation_id=uuid4(), status=status,
                              is_sellable=index != 1, **audit())
        products.append(product)
        presentations.append(presentation)
    person, organization = uuid4(), uuid4()
    customers = [
        insert(owners, "cr", "company_customers", id=uuid4(), company_id=company, customer_kind=PERSON,
               person_identity_id=person, internal_code=f"C-{uuid4().hex[:6]}", display_name="Cliente persona", **audit()),
        insert(owners, "cr", "company_customers", id=uuid4(), company_id=company, customer_kind=ORGANIZATION,
               organization_identity_id=organization, internal_code=f"C-{uuid4().hex[:6]}",
               display_name="Cliente organización", status="INACTIVE", **audit()),
        insert(owners, "cr", "company_customers", id=uuid4(), company_id=other, customer_kind=PERSON,
               person_identity_id=person, internal_code=f"C-{uuid4().hex[:6]}", display_name="Cliente ajeno", **audit()),
    ]
    price_list = insert(owners, "cr", "price_lists", id=uuid4(), company_id=company, code=f"L-{uuid4().hex[:6]}",
                        name="Lista ficticia", currency_code="COP", status="INACTIVE", **audit())
    return {"company": company, "other": other, "products": products, "presentations": presentations,
            "customers": customers, "person": person, "organization": organization, "price_list": price_list}


def _batch(rows, names):
    by_id = {str(row["id"]): row for row in rows}

    def handler(request: httpx.Request):
        ids = json.loads(request.content)["ids"] if b"ids" in request.content else json.loads(request.content)
        items = [{"id": value, "found": False} if value not in by_id else {"found": True, **body(by_id[value], *names)}
                 for value in ids]
        return 200, {"items": items}

    return handler


def test_commercial_directory_matches_http(owners, commercial):
    product_names = ("id", "company_id", "global_product_id", "internal_code", "display_name", "is_sellable",
                     "inventory_control_enabled", "status")
    presentation_names = ("id", "company_id", "company_product_id", "global_product_presentation_id", "is_sellable", "status")
    customer_names = ("id", "company_id", "customer_kind", "person_identity_id", "organization_identity_id",
                      "display_name", "status")
    routes = {
        ("POST", "/api/v1/company-products/batch-lookup"): _batch(commercial["products"], product_names),
        ("POST", "/api/v1/company-product-presentations/batch-lookup"): _batch(commercial["presentations"], presentation_names),
        ("GET", f"/api/v1/price-lists/{commercial['price_list']['id']}"): (200, body(commercial["price_list"], "id", "company_id", "status")),
    }
    for customer in commercial["customers"]:
        routes[("GET", f"/api/v1/company-customers/{customer['id']}")] = (
            200, {name: _json(customer.get(name, "ACTIVE" if name == "status" else None)) for name in customer_names})
    double = http(HTTPCommercialDirectory, routes)
    contract = ContractCommercialDirectory(engine=owners["cr"]["reader"], http=double)

    product_ids = [row["id"] for row in commercial["products"]] + [uuid4()]
    presentation_ids = [row["id"] for row in commercial["presentations"]] + [uuid4()]
    assert contract.lookup_products(product_ids) == double.lookup_products(product_ids)
    assert contract.lookup_presentations(presentation_ids) == double.lookup_presentations(presentation_ids)
    assert len(contract.lookup_products(product_ids)) == 3
    for customer in commercial["customers"]:
        assert contract.get_customer(customer["id"]) == double.get_customer(customer["id"])
    assert contract.get_price_list(commercial["price_list"]["id"]) == double.get_price_list(commercial["price_list"]["id"])
    assert contract.get_customer(uuid4()) is None
    assert contract.get_price_list(uuid4()) is None


def test_lookups_in_batches_of_100(owners, commercial):
    contract = ContractCommercialDirectory(engine=owners["cr"]["reader"], http=None)
    many = [uuid4() for _ in range(230)] + [commercial["products"][0]["id"]]
    assert list(contract.lookup_products(many)) == [commercial["products"][0]["id"]]


# --------------------------------------------------------------------------- clientes por identidad


@pytest.fixture(scope="module")
def access(owners):
    return seed_access_world(owners["oc"]["admin"])


CUSTOMER_READ = "perm:commercial-relationship:company_customers:read"
OC_READ = "perm:operational-context:application_users:read"


def test_customer_registry_matches_http(owners, commercial, access):
    member = next(case for case in access if case.name == "permitido_empresa")
    # La búsqueda filtra por la empresa del usuario: se registran clientes en esa empresa.
    person = uuid4()
    customer = insert(owners, "cr", "company_customers", id=uuid4(), company_id=member.company_id, customer_kind=PERSON,
                      person_identity_id=person, internal_code=f"C-{uuid4().hex[:6]}", display_name="Cliente miembro",
                      **audit())
    items = [{"id": str(customer["id"]), "company_id": str(member.company_id), "customer_kind": PERSON,
              "person_identity_id": str(person), "organization_identity_id": None, "display_name": "Cliente miembro",
              "status": "ACTIVE"}]
    double = HTTPCustomerRegistry(
        base_url="http://owner.test/api/v1", authorization="Bearer x", timeout_seconds=2,
        transport=routed({("GET", f"/api/v1/companies/{member.company_id}/company-customers"): (200, {"items": items})}),
    )
    contract = ContractCustomerRegistry(
        engine=owners["cr"]["reader"], access_engine=owners["oc"]["reader"],
        claims=claims(member.subject, CUSTOMER_READ, OC_READ), http=double,
    )
    identities = [person, uuid4()]
    assert contract.find(member.company_id, PERSON, identities) == double.find(member.company_id, PERSON, identities)
    assert contract.find(member.company_id, PERSON, []) == {}


@pytest.mark.parametrize("roles", [(CUSTOMER_READ,), (OC_READ,)], ids=["sin_permiso_oc", "sin_permiso_clientes"])
def test_customer_registry_without_permission_is_unavailable_like_403(owners, access, roles):
    member = next(case for case in access if case.name == "permitido_empresa")
    contract = ContractCustomerRegistry(engine=owners["cr"]["reader"], access_engine=owners["oc"]["reader"],
                                        claims=claims(member.subject, *roles), http=None)
    with pytest.raises(DependencyUnavailableError) as info:
        contract.find(member.company_id, PERSON, [uuid4()])
    assert info.value.provider == "commercial-relationship"


def test_customer_registry_non_member_is_unavailable_like_404(owners, access):
    stranger = next(case for case in access if case.name == "membresia_inactiva_mas_reciente")
    contract = ContractCustomerRegistry(engine=owners["cr"]["reader"], access_engine=owners["oc"]["reader"],
                                        claims=claims(stranger.subject, CUSTOMER_READ, OC_READ), http=None)
    with pytest.raises(DependencyUnavailableError):
        contract.find(stranger.company_id, PERSON, [uuid4()])


# --------------------------------------------------------------------------- Party Identity


@pytest.fixture(scope="module")
def identities(owners):
    tag = secrets.token_hex(3).upper()
    country = uuid4()
    people = []
    for index, (first, last, status) in enumerate(
        (("ANA", "ZULUAGA", "ACTIVE"), ("BETO", "ALVAREZ", "ACTIVE"), ("CARLA", "ALVAREZ", "ACTIVE"),
         ("DORA", "MESA", "INACTIVE"), ("ELSA", "MESA", "ACTIVE")),
    ):
        people.append(insert(owners, "pi", "person_identities", id=uuid4(), identification_country_id=country,
                             identification_type="CC", identification_number=f"{tag}{index:04d}", first_name=first,
                             middle_name=None, last_name=last, second_last_name=f"P{tag}" if index % 2 else None,
                             status=status, verification_status="UNVERIFIED", **audit()))
    organizations = []
    for index, (legal, trade, status) in enumerate(
        ((f"BETA {tag} SAS", None, "ACTIVE"), (f"ALFA {tag} SAS", f"ALFITA {tag}", "ACTIVE"), (f"GAMA {tag} SAS", None, "INACTIVE")),
    ):
        organizations.append(insert(owners, "pi", "organization_identities", id=uuid4(), country_id=country,
                                    identification_type="NIT", identification_number=f"9{tag}{index:03d}",
                                    legal_name=legal, trade_name=trade, status=status, **audit()))
    return {"tag": tag, "people": people, "organizations": organizations}


PERSON_NAMES = ("id", "identification_type", "identification_number", "first_name", "middle_name", "last_name",
                "second_last_name", "status")
ORG_NAMES = ("id", "identification_type", "identification_number", "legal_name", "trade_name", "status")


def test_party_get_matches_http(owners, identities):
    routes = {}
    for row in identities["people"]:
        routes[("GET", f"/api/v1/person-identities/{row['id']}")] = (200, body(row, *PERSON_NAMES))
    for row in identities["organizations"]:
        routes[("GET", f"/api/v1/organization-identities/{row['id']}")] = (200, body(row, *ORG_NAMES))
    double = http(HTTPPartyDirectory, routes)
    contract = ContractPartyDirectory(engine=owners["pi"]["reader"])
    for row in identities["people"]:
        assert contract.get_person(row["id"]) == double.get_person(row["id"])
    for row in identities["organizations"]:
        assert contract.get_organization(row["id"]) == double.get_organization(row["id"])
    assert contract.get_person(uuid4()) is None
    assert contract.get_organization(uuid4()) is None


def _expected_search(rows, fields, order, search, page, page_size):
    needle = search.strip().lower() if search and search.strip() else None
    found = [row for row in rows if row["status"] == "ACTIVE"
             and (needle is None or any(needle in (row[field] or "").lower() for field in fields))]
    found.sort(key=lambda row: tuple(str(row[key]) for key in order))
    start = (page - 1) * page_size
    return found[start : start + page_size], len(found)


@pytest.mark.parametrize(
    ("kind", "search", "page", "page_size"),
    [(PERSON, "ALVAREZ", 1, 1), (PERSON, "ALVAREZ", 2, 1), (PERSON, " mesa ", 1, 10), (PERSON, "{tag}", 1, 2),
     (ORGANIZATION, "{tag}", 1, 10), (ORGANIZATION, "alfita", 1, 10), (ORGANIZATION, "   ", 1, 100)],
)
def test_party_search_matches_owner_order_and_count(owners, identities, kind, search, page, page_size):
    """Mismo filtro, orden y conteo que `GET /person-identities` y `/organization-identities` (status=ACTIVE)."""
    tag = identities["tag"]
    text_value = search.replace("{tag}", tag)
    if kind == PERSON:
        rows, fields, order = identities["people"], ("identification_number", "first_name", "middle_name", "last_name",
                                                     "second_last_name"), ("last_name", "first_name", "id")
    else:
        rows, fields, order = identities["organizations"], ("identification_number", "legal_name", "trade_name"), (
            "legal_name", "id")
    contract = ContractPartyDirectory(engine=owners["pi"]["reader"])
    result = contract.search(kind, text_value, page, page_size)
    if text_value.strip():
        expected, total = _expected_search(rows, fields, order, text_value, page, page_size)
        assert [item.id for item in result.items] == [row["id"] for row in expected]
        assert result.total_records == total
    else:
        # Sin texto no filtra: incluye las identidades activas de esta prueba (y las de otras, si las hay).
        ids = {item.id for item in result.items}
        assert {row["id"] for row in rows if row["status"] == "ACTIVE"} <= ids


# --------------------------------------------------------------------------- Inventory


@pytest.fixture(scope="module")
def stock(owners):
    company, branch, user = uuid4(), uuid4(), uuid4()
    with_balance, without_balance = uuid4(), uuid4()
    insert(owners, "inv", "inventory_balances", company_id=company, branch_id=branch, company_product_id=with_balance,
           quantity=Decimal("7.5000"), **audit())
    key, operation = uuid4(), uuid4()
    insert(owners, "inv", "inventory_operations", id=operation, operation_key=key, requested_by_client="sales-service",
           operation_type="OUTPUT", company_id=company, branch_id=branch, origin_type="SALE", origin_id=uuid4(),
           application_user_id=user, correlation_id=uuid4(), line_count=2,
           request_hash=hashlib.sha256(b"t048").hexdigest(), created_by=WHO)
    details = [uuid4(), uuid4()]
    for index, detail in enumerate(details):
        insert(owners, "inv", "inventory_movements", operation_id=operation, company_id=company, branch_id=branch,
               company_product_id=with_balance, movement_type="SALE_OUTPUT", quantity=Decimal("1"),
               previous_balance=Decimal("10") - index, new_balance=Decimal("9") - index, balance_sequence=index + 1,
               origin_type="SALE", origin_id=uuid4(), origin_detail_id=detail, line_index=index,
               application_user_id=user, correlation_id=uuid4(), unit_cost=Decimal("1250.1250"),
               movement_value=Decimal("1250.13"), cost_known=index == 0, **audit())
    return {"company": company, "branch": branch, "with": with_balance, "without": without_balance, "key": key,
            "operation": operation, "details": details}


def test_inventory_reads_match_http(owners, stock):
    movements = [{"origin_detail_id": str(detail), "unit_cost": "1250.1250", "movement_value": "1250.13",
                  "cost_known": index == 0} for index, detail in enumerate(stock["details"])]
    double = http(HTTPInventoryGateway, {
        ("POST", f"/api/v1/companies/{stock['company']}/branches/{stock['branch']}/balances/lookup"):
            (200, {"items": [{"company_product_id": str(stock["with"]), "quantity": "7.5000"},
                             {"company_product_id": str(stock["without"]), "quantity": "0"}]}),
        ("GET", f"/api/v1/companies/{stock['company']}/inventory-operations/by-key/{stock['key']}"):
            (200, {"id": str(stock["operation"]), "operation_type": "OUTPUT", "reverses_operation_id": None,
                   "movements": movements}),
    })
    contract = ContractInventoryGateway(engine=owners["inv"]["reader"], http=double)
    ids = [stock["with"], stock["without"]]
    assert contract.lookup_balances(stock["company"], stock["branch"], ids) == double.lookup_balances(
        stock["company"], stock["branch"], ids)
    assert contract.lookup_balances(stock["company"], stock["branch"], ids)[stock["without"]].quantity == 0
    assert contract.find_by_key(stock["company"], stock["key"]) == double.find_by_key(stock["company"], stock["key"])
    assert contract.find_by_key(stock["company"], uuid4()) is None
    assert contract.find_by_key(uuid4(), stock["key"]) is None


# --------------------------------------------------------------------------- Operational Context


def test_operational_context_directory_reads_views(owners, access):
    branch_case = next(case for case in access if case.name == "permitido_sucursal")
    company_id, user_id = branch_case.expected.company_id, branch_case.expected.application_user_id
    contract = ContractOperationalContextDirectory(engine=owners["oc"]["reader"])
    with owners["oc"]["admin"].connect() as connection:
        company = connection.execute(
            text("SELECT status, default_currency, organization_identity_id FROM companies WHERE id = :i"), {"i": company_id}
        ).mappings().one()
        branch = connection.execute(text("SELECT company_id, status FROM branches WHERE id = :i"),
                                    {"i": branch_case.branch_id}).mappings().one()
        user = connection.execute(text("SELECT company_id, status FROM application_users WHERE id = :i"),
                                  {"i": user_id}).mappings().one()
    timezone = contract.get_branch(branch_case.branch_id).effective_timezone
    double = http(HTTPOperationalContextDirectory, {
        ("GET", f"/api/v1/companies/{company_id}"): (200, {"id": str(company_id), **{k: _json(v) for k, v in company.items()}}),
        ("GET", f"/api/v1/branches/{branch_case.branch_id}"): (200, {
            "id": str(branch_case.branch_id), "company_id": str(branch["company_id"]), "status": branch["status"],
            "effective_timezone": timezone}),
        ("GET", f"/api/v1/application-users/{user_id}"): (200, {"id": str(user_id), **{k: _json(v) for k, v in user.items()}}),
    })
    assert contract.get_company(company_id) == double.get_company(company_id)
    assert contract.get_branch(branch_case.branch_id) == double.get_branch(branch_case.branch_id)
    assert contract.get_application_user(user_id) == double.get_application_user(user_id)
    missing = uuid4()
    assert contract.get_company(missing) is None
    assert contract.get_branch(missing) is None
    assert contract.get_application_user(missing) is None


# --------------------------------------------------------------------------- base detenida


@pytest.mark.parametrize(
    ("key", "call", "provider"),
    [
        ("pc", lambda engine: ContractCatalogDirectory(engine=engine).get_product(uuid4()), "product-catalog"),
        ("pr", lambda engine: ContractPaymentReferenceDirectory(engine=engine).get_payment_method(uuid4()), "payment-reference"),
        ("cr", lambda engine: ContractCommercialDirectory(engine=engine, http=None).lookup_products([uuid4()]),
         "commercial-relationship"),
        ("pi", lambda engine: ContractPartyDirectory(engine=engine).search(PERSON, None, 1, 10), "party-identity"),
        ("inv", lambda engine: ContractInventoryGateway(engine=engine, http=None).find_by_key(uuid4(), uuid4()), "inventory"),
        ("oc", lambda engine: ContractOperationalContextDirectory(engine=engine).get_company(uuid4()), "operational-context"),
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
