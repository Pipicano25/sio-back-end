"""Adaptadores de contrato de la compra frente a sus adaptadores HTTP con los mismos datos (spec 025, T055).

Crea en el contenedor de pruebas de Purchase las bases ``purchase_test__{pc,cr,pi,pr,inv,oc}`` con las migraciones
reales de cada propietario, el rol ``pur_contract_reader`` con su ``contract/grants.yaml``, y comprueba para cada
método:

- mismo resultado que el adaptador HTTP cuando el propietario responde lo que respondería con esos datos;
- "no encontrado" igual que el ``404`` (o ``found=false``) de hoy;
- base detenida → la misma ``DependencyUnavailableError(<proveedor>)`` que hoy produce el ``503``.

La cobertura de políticas (`v1_pricing_coverage`) se compara con el endpoint real en
``CR/tests/contract_views/test_purchase_views_parity.py``; aquí se comprueba que el adaptador la consulta igual.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sio_contract_read.testing_oc import seed_access_world
from sqlalchemy import create_engine, text

from purchase_service.application.exceptions import DependencyUnavailableError
from purchase_service.infrastructure.commercial_relationship_directory import HTTPCommercialDirectory
from purchase_service.infrastructure.contract_commercial_relationship import ContractCommercialDirectory
from purchase_service.infrastructure.contract_inventory import ContractInventoryGateway
from purchase_service.infrastructure.contract_operational_context import ContractOperationalContextDirectory
from purchase_service.infrastructure.contract_party_identity import ContractPartyDirectory
from purchase_service.infrastructure.contract_payment_reference import ContractPaymentReferenceDirectory
from purchase_service.infrastructure.contract_product_catalog import ContractCatalogDirectory
from purchase_service.infrastructure.inventory_gateway import HTTPInventoryGateway
from purchase_service.infrastructure.operational_context_directory import HTTPOperationalContextDirectory
from purchase_service.infrastructure.party_identity_directory import HTTPPartyDirectory
from purchase_service.infrastructure.payment_reference_directory import HTTPPaymentReferenceDirectory
from purchase_service.infrastructure.product_catalog_directory import HTTPCatalogDirectory
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
    # Los roles son del servidor: en este contenedor las seis bases comparten `pur_contract_reader` y su contraseña.
    password = secrets.token_urlsafe(24)
    for key, service in OWNERS.items():
        owner = SERVICES / service
        url = create_owner_schema(test_database_url, f"purchase_test__{key}", owner, OWNER_ENV, recreate=True)
        reader_url = provision_reader(url, owner / "contract" / "grants.yaml", "purchase", password)
        settings = ContractReadSettings(prefix=key.upper(), source="contract", database_url=reader_url, timeout_seconds=2)
        result[key] = {"admin": create_engine(url), "reader": create_contract_engine(settings, application_name="t055")}
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
        database_url=f"postgresql+psycopg://pur_contract_reader:x@127.0.0.1:1/purchase_test__{key}",
    )
    return create_contract_engine(settings, application_name="t055")


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
    if isinstance(value, UUID | Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def body(row: dict, *names: str, **extra) -> dict:
    return {**{name: _json(row.get(name)) for name in names}, **{k: _json(v) for k, v in extra.items()}}


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


def _presentations_batch(rows):
    by_id = {str(row["id"]): row for row in rows}

    def handler(request: httpx.Request):
        import json

        ids = json.loads(request.content)["ids"]
        return 200, {"items": [
            {"id": value, "found": False} if value not in by_id
            else {"found": True, **body(by_id[value], "id", "code", "name", "base_quantity")}
            for value in ids
        ]}

    return handler


def test_catalog_matches_http(owners, catalog):
    contract = ContractCatalogDirectory(engine=owners["pc"]["reader"])
    presentations = [catalog[status]["presentation"] for status in ("ACTIVE", "INACTIVE")]
    routes = {("POST", "/api/v1/presentations/batch-lookup"): _presentations_batch(presentations),
              ("GET", f"/api/v1/units-of-measure/{catalog['unit']['id']}"): (200, body(catalog["unit"], "id", "code"))}
    for status in ("ACTIVE", "INACTIVE"):
        product, presentation = catalog[status]["product"], catalog[status]["presentation"]
        routes[("GET", f"/api/v1/presentations/{presentation['id']}")] = (
            200, body(presentation, "id", "code", "name", "base_quantity", "status"))
        routes[("GET", f"/api/v1/products/{product['id']}")] = (200, body(product, "id", "base_unit_id", "status"))
    double = http(HTTPCatalogDirectory, routes)
    for status in ("ACTIVE", "INACTIVE"):
        product, presentation = catalog[status]["product"], catalog[status]["presentation"]
        assert contract.get_presentation(presentation["id"]) == double.get_presentation(presentation["id"])
        assert contract.get_product(product["id"]) == double.get_product(product["id"])
    assert contract.get_unit(catalog["unit"]["id"]) == double.get_unit(catalog["unit"]["id"])
    ids = [row["id"] for row in presentations] + [uuid4()]
    assert contract.lookup_presentations(ids) == double.lookup_presentations(ids)
    assert len(contract.lookup_presentations(ids)) == 2
    missing = uuid4()
    assert contract.get_presentation(missing) is None
    assert contract.get_product(missing) is None
    assert contract.get_unit(missing) is None


def test_catalog_presentations_in_batches_of_100(owners, catalog):
    contract = ContractCatalogDirectory(engine=owners["pc"]["reader"])
    known = catalog["ACTIVE"]["presentation"]["id"]
    assert list(contract.lookup_presentations([uuid4() for _ in range(230)] + [known])) == [known]


# --------------------------------------------------------------------------- Payment Reference


def test_payment_reference_matches_http(owners):
    now = datetime.now(UTC)
    contract = ContractPaymentReferenceDirectory(engine=owners["pr"]["reader"])
    for status in ("ACTIVE", "INACTIVE"):
        method = insert(owners, "pr", "global_payment_methods", id=uuid4(), code=f"M{secrets.token_hex(3).upper()}",
                        name=f"Medio ficticio {status}", method_type="CASH", status=status, created_at=now,
                        updated_at=now, **audit())
        kind = insert(owners, "pr", "global_payment_condition_types", id=uuid4(),
                      code=f"T{secrets.token_hex(3).upper()}", name=f"Tipo ficticio {status}", status=status,
                      created_at=now, updated_at=now, **audit())
        double = http(HTTPPaymentReferenceDirectory, {
            ("GET", f"/global-payment-methods/{method['id']}"): (200, body(method, "id", "code", "name", "status")),
            ("GET", f"/global-payment-condition-types/{kind['id']}"): (200, body(kind, "id", "code", "name", "status")),
        }, base="http://owner.test")
        assert contract.get_payment_method(method["id"]) == double.get_payment_method(method["id"])
        assert contract.get_condition_type(kind["id"]) == double.get_condition_type(kind["id"])
    assert contract.get_payment_method(uuid4()) is None
    assert contract.get_condition_type(uuid4()) is None


# --------------------------------------------------------------------------- Party Identity


def test_organization_matches_http(owners):
    tag = secrets.token_hex(3).upper()
    country = uuid4()
    rows = [
        insert(owners, "pi", "organization_identities", id=uuid4(), country_id=country, identification_type="NIT",
               identification_number=f"9{tag}{index}", legal_name=f"PROVEEDOR {tag} {index}", trade_name=None,
               status=status, **audit())
        for index, status in enumerate(("ACTIVE", "INACTIVE"))
    ]
    routes = {("GET", f"/api/v1/organization-identities/{row['id']}"): (
        200, body(row, "id", "identification_type", "identification_number", "legal_name", "status")) for row in rows}
    double = http(HTTPPartyDirectory, routes)
    contract = ContractPartyDirectory(engine=owners["pi"]["reader"])
    for row in rows:
        assert contract.get_organization(row["id"]) == double.get_organization(row["id"])
    assert contract.get_organization(uuid4()) is None


# --------------------------------------------------------------------------- Commercial Relationship


@pytest.fixture(scope="module")
def commercial(owners):
    company, other = uuid4(), uuid4()
    products, presentations = [], []
    for index, (owner_company, status) in enumerate(((company, "ACTIVE"), (company, "INACTIVE"), (other, "ACTIVE"))):
        product = insert(owners, "cr", "company_products", id=uuid4(), company_id=owner_company, global_product_id=uuid4(),
                         internal_code=f"P-{index}-{uuid4().hex[:6]}", display_name=f"Producto ficticio {index}",
                         currency_code="COP", status=status, is_purchasable=index != 1,
                         inventory_control_enabled=index == 0,
                         purchase_tax_percentage=Decimal("19.0000") if index == 0 else None, **audit())
        presentation = insert(owners, "cr", "company_product_presentations", id=uuid4(), company_id=owner_company,
                              company_product_id=product["id"], global_product_presentation_id=uuid4(), status=status,
                              is_purchasable=index != 1, **audit())
        products.append(product)
        presentations.append(presentation)
    suppliers = [
        insert(owners, "cr", "company_suppliers", id=uuid4(), company_id=owner_company, organization_identity_id=uuid4(),
               internal_code=f"S-{index}-{uuid4().hex[:6]}", display_name=f"Proveedor ficticio {index}", status=status,
               block_reason="Prueba" if status == "BLOCKED" else None, **audit())
        for index, (owner_company, status) in enumerate(((company, "ACTIVE"), (company, "BLOCKED"), (other, "INACTIVE")))
    ]
    conditions = [
        insert(owners, "cr", "supplier_payment_conditions", id=uuid4(), company_id=company,
               company_supplier_id=suppliers[0]["id"], payment_condition_type_id=uuid4(), currency_code="COP",
               payment_terms_days=days, is_default=index == 0, valid_from=datetime(2026, 1, 1, 3, 30, tzinfo=UTC),
               valid_to=datetime(2026, 12, 31, 23, 0, tzinfo=UTC) if index else None, status=status, **audit())
        for index, (days, status) in enumerate(((30, "ACTIVE"), (60, "INACTIVE")))
    ]
    supplier_products = [
        insert(owners, "cr", "supplier_products", id=uuid4(), company_id=company, company_supplier_id=suppliers[0]["id"],
               company_product_id=products[0]["id"],
               company_product_presentation_id=presentations[0]["id"] if index == 0 else None,
               purchase_unit_id=uuid4(), minimum_order_quantity=Decimal("1"), pack_quantity=Decimal("1"),
               currency_code="COP", expected_supplier_lead_time_hours=Decimal("48.00") if index == 0 else None,
               is_preferred=index == 0, status=status, **audit())
        for index, status in enumerate(("ACTIVE", "INACTIVE"))
    ]
    return {"company": company, "other": other, "products": products, "presentations": presentations,
            "suppliers": suppliers, "conditions": conditions, "supplier_products": supplier_products}


def _batch(rows, names):
    by_id = {str(row["id"]): row for row in rows}

    def handler(request: httpx.Request):
        import json

        ids = json.loads(request.content)["ids"]
        items = [{"id": value, "found": False} if value not in by_id else {"found": True, **body(by_id[value], *names)}
                 for value in ids]
        return 200, {"items": items}

    return handler


def test_commercial_directory_matches_http(owners, commercial):
    product_names = ("id", "company_id", "global_product_id", "internal_code", "display_name", "is_purchasable",
                     "inventory_control_enabled", "status", "purchase_tax_percentage")
    presentation_names = ("id", "company_id", "company_product_id", "global_product_presentation_id", "is_purchasable",
                          "status")
    routes = {
        ("POST", "/api/v1/company-products/batch-lookup"): _batch(commercial["products"], product_names),
        ("POST", "/api/v1/company-product-presentations/batch-lookup"): _batch(commercial["presentations"],
                                                                                presentation_names),
    }
    for row in commercial["suppliers"]:
        routes[("GET", f"/api/v1/company-suppliers/{row['id']}")] = (
            200, body(row, "id", "company_id", "organization_identity_id", "display_name", "status"))
    for row in commercial["conditions"]:
        routes[("GET", f"/api/v1/supplier-payment-conditions/{row['id']}")] = (
            200, body(row, "id", "company_id", "company_supplier_id", "payment_condition_type_id", "currency_code",
                      "payment_terms_days", "valid_from", "valid_to", "status"))
    for row in commercial["supplier_products"]:
        routes[("GET", f"/api/v1/supplier-products/{row['id']}")] = (
            200, body(row, "id", "company_id", "company_supplier_id", "company_product_id",
                      "company_product_presentation_id", "expected_supplier_lead_time_hours", "status"))
    double = http(HTTPCommercialDirectory, routes)
    contract = ContractCommercialDirectory(engine=owners["cr"]["reader"])

    product_ids = [row["id"] for row in commercial["products"]] + [uuid4()]
    presentation_ids = [row["id"] for row in commercial["presentations"]] + [uuid4()]
    assert contract.lookup_products(product_ids) == double.lookup_products(product_ids)
    assert contract.lookup_presentations(presentation_ids) == double.lookup_presentations(presentation_ids)
    assert len(contract.lookup_products(product_ids)) == 3
    for row in commercial["suppliers"]:
        assert contract.get_supplier(row["id"]) == double.get_supplier(row["id"])
    for row in commercial["conditions"]:
        assert contract.get_payment_condition(row["id"]) == double.get_payment_condition(row["id"])
    for row in commercial["supplier_products"]:
        assert contract.get_supplier_product(row["id"]) == double.get_supplier_product(row["id"])
    missing = uuid4()
    assert contract.get_supplier(missing) is None
    assert contract.get_payment_condition(missing) is None
    assert contract.get_supplier_product(missing) is None


def test_commercial_lookups_in_batches_of_100(owners, commercial):
    contract = ContractCommercialDirectory(engine=owners["cr"]["reader"])
    many = [uuid4() for _ in range(230)] + [commercial["products"][0]["id"]]
    assert list(contract.lookup_products(many)) == [commercial["products"][0]["id"]]


# --------------------------------------------------------------------------- Inventory


def test_inventory_find_by_key_matches_http(owners):
    company, branch, user = uuid4(), uuid4(), uuid4()
    key, operation = uuid4(), uuid4()
    insert(owners, "inv", "inventory_operations", id=operation, operation_key=key, requested_by_client="purchase-service",
           operation_type="ENTRY", company_id=company, branch_id=branch, origin_type="PURCHASE", origin_id=uuid4(),
           application_user_id=user, correlation_id=uuid4(), line_count=1,
           request_hash=hashlib.sha256(b"t055").hexdigest(), created_by=WHO)
    double = http(HTTPInventoryGateway, {
        ("GET", f"/api/v1/companies/{company}/inventory-operations/by-key/{key}"):
            (200, {"id": str(operation), "operation_type": "ENTRY", "reverses_operation_id": None, "movements": []}),
    })
    contract = ContractInventoryGateway(engine=owners["inv"]["reader"], http=double)
    assert contract.find_by_key(company, key) == double.find_by_key(company, key)
    assert contract.find_by_key(company, uuid4()) is None
    assert contract.find_by_key(uuid4(), key) is None


# --------------------------------------------------------------------------- Operational Context


@pytest.fixture(scope="module")
def access(owners):
    return seed_access_world(owners["oc"]["admin"])


def test_operational_context_directory_reads_views(owners, access):
    branch_case = next(case for case in access if case.name == "permitido_sucursal")
    company_id, user_id = branch_case.expected.company_id, branch_case.expected.application_user_id
    contract = ContractOperationalContextDirectory(engine=owners["oc"]["reader"])
    with owners["oc"]["admin"].connect() as connection:
        company = connection.execute(
            text("SELECT status, default_currency FROM companies WHERE id = :i"), {"i": company_id}
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
        ("pc", lambda engine: ContractCatalogDirectory(engine=engine).lookup_presentations([uuid4()]), "product-catalog"),
        ("pr", lambda engine: ContractPaymentReferenceDirectory(engine=engine).get_condition_type(uuid4()),
         "payment-reference"),
        ("cr", lambda engine: ContractCommercialDirectory(engine=engine).get_supplier(uuid4()), "commercial-relationship"),
        ("cr", lambda engine: ContractCommercialDirectory(engine=engine).lookup_pricing_coverage(uuid4(), "COP", [uuid4()]),
         "commercial-relationship"),
        ("pi", lambda engine: ContractPartyDirectory(engine=engine).get_organization(uuid4()), "party-identity"),
        ("inv", lambda engine: ContractInventoryGateway(engine=engine, http=None).find_by_key(uuid4(), uuid4()), "inventory"),
        ("oc", lambda engine: ContractOperationalContextDirectory(engine=engine).get_branch(uuid4()), "operational-context"),
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


# --------------------------------------------------------------------------- cobertura de políticas


def test_pricing_coverage_matches_http(owners, commercial):
    """`found` = la presentación es de la empresa; `covered` = hay política vigente en la moneda pedida. La regla de
    vigencia de la vista se compara con el endpoint real en CR (T050); aquí, que el adaptador responda igual."""
    company = commercial["company"]
    covered, plain, foreign = (commercial["presentations"][0]["id"], commercial["presentations"][1]["id"],
                               commercial["presentations"][2]["id"])
    price_list = insert(owners, "cr", "price_lists", id=uuid4(), company_id=company, code=f"COB-{uuid4().hex[:6]}",
                        name="Lista ficticia de cobertura", currency_code="COP", **audit())
    policy = insert(owners, "cr", "price_list_pricing_policies", id=uuid4(), company_id=company,
                    price_list_id=price_list["id"], name="Política ficticia", **audit())
    insert(owners, "cr", "price_list_pricing_policy_terms", id=uuid4(), policy_id=policy["id"],
           markup_percentage=Decimal("30"), valid_from=datetime(2026, 1, 1, tzinfo=UTC), created_by=WHO)
    insert(owners, "cr", "price_list_pricing_policy_presentations", id=uuid4(), company_id=company,
           policy_id=policy["id"], price_list_id=price_list["id"], company_product_presentation_id=covered,
           valid_from=datetime(2026, 1, 1, tzinfo=UTC), created_by=WHO)
    missing = uuid4()
    ids = [covered, plain, foreign, missing]

    def coverage(request: httpx.Request):
        import json

        payload = json.loads(request.content)
        cop = payload["currency_code"] == "COP"
        return 200, {"items": [
            {"company_product_presentation_id": value, "found": value in {str(covered), str(plain)},
             "covered": cop and value == str(covered)}
            for value in payload["company_product_presentation_ids"]]}

    double = http(HTTPCommercialDirectory, {("POST", f"/api/v1/companies/{company}/pricing-policies/coverage"): coverage})
    contract = ContractCommercialDirectory(engine=owners["cr"]["reader"])
    for currency in ("COP", "USD"):
        assert contract.lookup_pricing_coverage(company, currency, ids) == double.lookup_pricing_coverage(
            company, currency, ids)
    assert contract.lookup_pricing_coverage(company, "COP", ids) == {covered: True, plain: False, foreign: False,
                                                                      missing: False}
    many = [uuid4() for _ in range(230)] + [covered]
    assert sum(contract.lookup_pricing_coverage(company, "COP", many).values()) == 1
