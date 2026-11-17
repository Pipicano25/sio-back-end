"""Adaptadores de contrato de PIQ frente a sus adaptadores HTTP con los mismos datos (spec 025, T073).

PIQ no tiene base propia: igual que ``test_access_directory.py``, la prueba crea en el servidor de la base de pruebas
de Operational Context las bases ``product_inventory_query_test__{pc,cr,inv}`` con las migraciones reales de cada
propietario y el rol ``piq_contract_reader`` con su ``contract/grants.yaml`` (una sola contraseña por ejecución: los
roles son del servidor). Sin URL de administrador, la prueba se omite.

Para cada lectura migrada comprueba:

- mismo resultado que el adaptador HTTP cuando el propietario responde lo que respondería con esos datos (filas en
  todos los estados, de otra empresa o sucursal, sin marca, sin saldo, sin política, ids inexistentes y repetidos);
- "no encontrado" igual que el ``found=false`` (o la ausencia) de hoy;
- lotes de 100 ids distintos;
- base detenida → la misma ``DependencyUnavailableError(<proveedor>)`` que hoy produce el ``503``, con causa
  ``contract:``;
- las lecturas que siguen por API (FR-036) se delegan al adaptador HTTP sin tocar la base;
- la selección por ``<PROPIETARIO>_READ_SOURCE`` en ``build_http_dependencies``.
"""

from __future__ import annotations

import asyncio
import json
import secrets
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sio_contract_read import ContractReadSettings, create_contract_engine
from sio_contract_read.testing import create_owner_schema, provision_reader
from sqlalchemy import create_engine, text

from product_inventory_query_service.api.dependencies import build_http_dependencies
from product_inventory_query_service.application.exceptions import DependencyUnavailableError
from product_inventory_query_service.application.ports import CatalogFilters, PriceLine, ProductCriteria
from product_inventory_query_service.infrastructure.commercial_relationship import HTTPCommercialRelationship
from product_inventory_query_service.infrastructure.contract_commercial_relationship import (
    ContractCommercialRelationship,
)
from product_inventory_query_service.infrastructure.contract_inventory import ContractInventory
from product_inventory_query_service.infrastructure.contract_product_catalog import ContractProductCatalog
from product_inventory_query_service.infrastructure.inventory import HTTPInventory
from product_inventory_query_service.infrastructure.product_catalog import HTTPProductCatalog
from tests.conftest import build_test_settings
from tests.contract.adapter_support import Recorder, technical
from tests.contract_reads.test_access_directory import admin_url

SERVICES = Path(__file__).resolve().parents[3]
OWNERS = {
    "pc": ("PRODUCT_CATALOG", "product-catalog-service"),
    "cr": ("COMMERCIAL_RELATIONSHIP", "commercial-relationship-service"),
    "inv": ("INVENTORY", "inventory-service"),
}
CONSUMER = "product-inventory-query"
WHO = "prueba-spec-025"


# --------------------------------------------------------------------------- infraestructura


@pytest.fixture(scope="module")
def owners():
    """URL de administrador, motor de administrador, ajustes y motor de lectura de cada propietario."""
    admin = admin_url()
    password = secrets.token_urlsafe(24)
    result = {}
    for key, (prefix, service) in OWNERS.items():
        owner = SERVICES / service
        url = create_owner_schema(admin, f"product_inventory_query_test__{key}", owner, recreate=True)
        reader_url = provision_reader(url, owner / "contract" / "grants.yaml", CONSUMER, password)
        settings = ContractReadSettings(prefix=prefix, source="contract", database_url=reader_url, timeout_seconds=2)
        result[key] = {
            "admin": create_engine(url),
            "settings": settings,
            "reader": create_contract_engine(settings, application_name="piq-t073"),
        }
    yield result
    for item in result.values():
        item["admin"].dispose()
        item["reader"].dispose()


def down_engine(key: str):
    prefix = OWNERS[key][0]
    settings = ContractReadSettings(
        prefix=prefix, source="contract", timeout_seconds=1, connect_timeout_seconds=1,
        database_url=f"postgresql+psycopg://piq_contract_reader:x@127.0.0.1:1/product_inventory_query_test__{key}",
    )
    return create_contract_engine(settings, application_name="piq-t073")


def insert(owners, key: str, table: str, **values) -> dict:
    columns = ", ".join(values)
    marks = ", ".join(f":{name}" for name in values)
    with owners[key]["admin"].begin() as connection:
        connection.execute(text(f"INSERT INTO public.{table} ({columns}) VALUES ({marks})"), values)
    return values


def audit(*, timestamps: bool = True) -> dict:
    now = datetime.now(UTC)
    values = {"created_by": WHO, "updated_by": WHO}
    if timestamps:
        values.update(created_at=now, updated_at=now)
    return values


def run(coroutine):
    return asyncio.run(coroutine)


def _json(value):
    if isinstance(value, UUID | Decimal):
        return str(value)
    return value


def refuse(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"solicitud HTTP inesperada: {request.method} {request.url.path}")


# --------------------------------------------------------------------------- Product Catalog


@pytest.fixture(scope="module")
def catalog(owners):
    tag = secrets.token_hex(3).upper()
    unit = insert(owners, "pc", "global_units_of_measure", id=uuid4(), code=f"U{tag}", name="Unidad ficticia",
                  symbol="u", measurement_type="UNIT", allows_decimals=False, status="ACTIVE", **audit())
    old_unit = insert(owners, "pc", "global_units_of_measure", id=uuid4(), code=f"V{tag}", name="Unidad retirada",
                      symbol="v", measurement_type="UNIT", allows_decimals=True, status="INACTIVE", **audit())
    brand = insert(owners, "pc", "global_brands", id=uuid4(), code=f"M{tag}", name="Marca ficticia",
                   status="INACTIVE", **audit())

    def product(name: str, status: str, brand_id=None, base_unit=unit) -> dict:
        return insert(owners, "pc", "global_products", id=uuid4(), product_type="GOOD", status=status,
                      canonical_name=f"{name} {tag}", canonical_name_key=uuid4().hex, base_unit_id=base_unit["id"],
                      global_brand_id=brand_id, **audit())

    full = product("PRODUCTO COMPLETO", "ACTIVE", brand["id"])
    bare = product("PRODUCTO SIN MARCA", "INACTIVE", base_unit=old_unit)
    categories = {
        code: insert(owners, "pc", "global_categories", id=uuid4(), code=f"{code}{tag}", name=f"Categoria {code}",
                     status="ACTIVE" if code != "ALFA" else "INACTIVE", **audit())
        for code in ("ZETA", "ALFA", "HIGIENE", "RETIRADA")
    }
    links = [("ZETA", False, "ACTIVE"), ("HIGIENE", True, "ACTIVE"), ("ALFA", False, "ACTIVE"),
             ("RETIRADA", False, "INACTIVE")]
    for code, primary, status in links:
        insert(owners, "pc", "global_product_categories", id=uuid4(), global_product_id=full["id"],
               global_category_id=categories[code]["id"], is_primary=primary, status=status, **audit())
    box = insert(owners, "pc", "global_product_presentations", id=uuid4(), global_product_id=full["id"], code="CAJA",
                 name="Caja", is_base=False, base_quantity=Decimal("12"), status="ACTIVE", **audit())
    identifiers = [
        ("OTHER", f"ZZ{tag}", False, None, "ACTIVE"),
        ("GTIN", "7702010000017", True, box["id"], "ACTIVE"),
        ("BARCODE", f"AA{tag}", False, None, "ACTIVE"),
        ("OTHER", f"OLD{tag}", False, None, "INACTIVE"),
    ]
    for kind, value, primary, presentation, status in identifiers:
        canonical = value.rjust(14, "0") if kind == "GTIN" else value
        insert(owners, "pc", "global_product_identifiers", id=uuid4(), global_product_id=full["id"],
               global_product_presentation_id=presentation, identifier_type=kind, value=value,
               canonical_value=canonical, is_primary=primary, status=status, **audit())
    return {"tag": tag, "unit": unit, "old_unit": old_unit, "brand": brand, "full": full, "bare": bare,
            "categories": categories, "box": box}


def _summary_body(catalog: dict, product: dict) -> dict:
    """PC-1 con esos datos (paridad con el endpoint real en PC/tests/contract_views/test_summary_views_parity.py)."""
    tag = catalog["tag"]
    unit = catalog["unit"] if product is catalog["full"] else catalog["old_unit"]
    body = {
        "id": str(product["id"]), "found": True, "canonical_name": product["canonical_name"], "product_type": "GOOD",
        "status": product["status"], "brand": None,
        "base_unit": {"id": str(unit["id"]), "code": unit["code"], "name": unit["name"]},
        "categories": [], "identifiers": [], "has_image": False, "image_asset_id": None, "image_url": None,
    }
    if product is catalog["full"]:
        brand = catalog["brand"]
        body["brand"] = {"id": str(brand["id"]), "code": brand["code"], "name": brand["name"]}
        body["categories"] = [
            {"id": str(catalog["categories"][code]["id"]), "code": f"{code}{tag}", "name": f"Categoria {code}",
             "is_primary": primary}
            for code, primary in (("HIGIENE", True), ("ALFA", False), ("ZETA", False))
        ]
        body["identifiers"] = [
            {"type": "GTIN", "value": "7702010000017", "is_primary": True,
             "global_product_presentation_id": str(catalog["box"]["id"])},
            {"type": "BARCODE", "value": f"AA{tag}", "is_primary": False, "global_product_presentation_id": None},
            {"type": "OTHER", "value": f"ZZ{tag}", "is_primary": False, "global_product_presentation_id": None},
        ]
    return body


def _pc_double(catalog: dict, recorder_calls: list | None = None) -> HTTPProductCatalog:
    products = {str(catalog[name]["id"]): catalog[name] for name in ("full", "bare")}
    units = {str(catalog[name]["id"]): catalog[name] for name in ("unit", "old_unit")}

    def handler(request: httpx.Request) -> httpx.Response:
        ids = json.loads(request.content)["ids"]
        if request.url.path.endswith("/products/summaries/batch-lookup"):
            items = [_summary_body(catalog, products[value]) if value in products else {"id": value, "found": False}
                     for value in ids]
        elif request.url.path.endswith("/units-of-measure/batch-lookup"):
            items = [{"id": value, "found": True, "code": units[value]["code"], "name": units[value]["name"],
                      "status": units[value]["status"]} if value in units else {"id": value, "found": False}
                     for value in ids]
        else:
            return httpx.Response(404, json={})
        return httpx.Response(200, json={"items": items})

    recorder = Recorder(handler)
    if recorder_calls is not None:
        recorder_calls.append(recorder)
    return HTTPProductCatalog(technical("product-catalog", recorder))


def test_summaries_match_http(owners, catalog):
    ids = [catalog["full"]["id"], uuid4(), catalog["bare"]["id"], catalog["full"]["id"]]
    expected = run(_pc_double(catalog).summaries(ids))
    contract = ContractProductCatalog(engine=owners["pc"]["reader"],
                                      http=HTTPProductCatalog(technical("product-catalog", Recorder(refuse))))
    observed = run(contract.summaries(ids))
    assert observed == expected
    assert list(observed) == list(expected)
    assert set(observed) == {catalog["full"]["id"], catalog["bare"]["id"]}
    assert observed[catalog["bare"]["id"]].brand is None
    assert [c.code for c in observed[catalog["full"]["id"]].categories][0].startswith("HIGIENE")
    assert run(contract.summaries([])) == {}


def test_units_match_http(owners, catalog):
    ids = [catalog["unit"]["id"], catalog["old_unit"]["id"], uuid4(), catalog["unit"]["id"]]
    expected = run(_pc_double(catalog).units(ids))
    contract = ContractProductCatalog(engine=owners["pc"]["reader"],
                                      http=HTTPProductCatalog(technical("product-catalog", Recorder(refuse))))
    assert run(contract.units(ids)) == expected
    assert len(expected) == 2
    assert run(contract.units([])) == {}


def test_catalog_reads_in_batches_of_100(owners, catalog):
    contract = ContractProductCatalog(engine=owners["pc"]["reader"],
                                      http=HTTPProductCatalog(technical("product-catalog", Recorder(refuse))))
    known = catalog["full"]["id"]
    assert list(run(contract.summaries([uuid4() for _ in range(230)] + [known]))) == [known]
    assert list(run(contract.units([uuid4() for _ in range(150)] + [catalog["unit"]["id"]]))) == [catalog["unit"]["id"]]


def test_catalog_api_reads_stay_on_http(catalog):
    """FR-036: `products/match` y `presentations` (URL firmada de imagen) siguen por API."""
    presentation = {"id": str(catalog["box"]["id"]), "found": True, "global_product_id": str(catalog["full"]["id"]),
                    "code": "CAJA", "name": "Caja", "status": "ACTIVE", "base_quantity": "12.0000", "has_image": False,
                    "image_asset_id": None, "image_url": None, "images": []}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products/match"):
            body = json.loads(request.content)
            if "candidate_ids" in body:
                return httpx.Response(200, json={"ids": body["candidate_ids"][:1]})
            return httpx.Response(200, json={"items": [], "has_more": False})
        return httpx.Response(200, json={"items": [presentation]})

    recorder = Recorder(handler)
    http = HTTPProductCatalog(technical("product-catalog", recorder))
    contract = ContractProductCatalog(engine=down_engine("pc"), http=http)
    candidate = uuid4()
    assert run(contract.match_candidates(CatalogFilters(), [candidate])) == [candidate]
    assert run(contract.match_page(CatalogFilters(), limit=5)) == ([], False)
    assert set(run(contract.presentations([catalog["box"]["id"]], include_images=True))) == {catalog["box"]["id"]}
    assert len(recorder.requests) == 3


# --------------------------------------------------------------------------- Commercial Relationship


@pytest.fixture(scope="module")
def commercial(owners):
    company, other = uuid4(), uuid4()
    products, presentations = [], []
    specs = [  # (empresa, estado, control de inventario)
        (company, "ACTIVE", True), (company, "ACTIVE", True), (company, "ACTIVE", False),
        (company, "INACTIVE", True), (other, "ACTIVE", True),
    ]
    for index, (owner, status, controlled) in enumerate(specs):
        product = insert(owners, "cr", "company_products", id=uuid4(), company_id=owner, global_product_id=uuid4(),
                         internal_code=f"P{index}{uuid4().hex[:6]}", display_name=f"Producto ficticio {index}",
                         currency_code="COP", status=status, inventory_control_enabled=controlled,
                         **audit(timestamps=False))
        products.append(product)
        for variant in range(2 if index == 0 else 1):
            presentations.append(insert(
                owners, "cr", "company_product_presentations", id=uuid4(), company_id=owner,
                company_product_id=product["id"], global_product_presentation_id=uuid4(),
                status="INACTIVE" if variant else status, is_sellable=variant == 0,
                sku=f"SKU{index}{variant}{uuid4().hex[:4]}" if variant == 0 else None, **audit(timestamps=False),
            ))
    return {"company": company, "other": other, "products": products, "presentations": presentations}


def _cr_double(commercial: dict) -> HTTPCommercialRelationship:
    """CR con esos datos: `total_records` del listado filtrado y CR-2 en orden `company_product_id, id`."""

    def handler(request: httpx.Request) -> httpx.Response:
        company = UUID(request.url.path.split("/companies/")[1].split("/")[0])
        if request.method == "GET" and request.url.path.endswith("/company-products"):
            total = sum(1 for row in commercial["products"] if row["company_id"] == company
                        and row["status"] == "ACTIVE" and row["inventory_control_enabled"])
            return httpx.Response(200, json={"items": [], "page": 1, "page_size": 1, "total_records": total,
                                             "total_pages": 1})
        ids = {UUID(value) for value in json.loads(request.content)["company_product_ids"]}
        rows = sorted((row for row in commercial["presentations"]
                       if row["company_id"] == company and row["company_product_id"] in ids),
                      key=lambda row: (str(row["company_product_id"]), str(row["id"])))
        items = [{name: _json(row.get(name)) for name in (
            "id", "company_id", "company_product_id", "global_product_presentation_id", "internal_code", "sku",
            "reference_code", "is_sellable", "status")} for row in rows]
        return httpx.Response(200, json={"items": items})

    return HTTPCommercialRelationship(technical("commercial-relationship", Recorder(handler)))


def test_count_adopted_matches_http(owners, commercial):
    contract = ContractCommercialRelationship(
        engine=owners["cr"]["reader"],
        http=HTTPCommercialRelationship(technical("commercial-relationship", Recorder(refuse))),
    )
    for company in (commercial["company"], commercial["other"], uuid4()):
        assert run(contract.count_adopted(company)) == run(_cr_double(commercial).count_adopted(company))
    assert run(contract.count_adopted(commercial["company"])) == 2


def test_presentations_by_products_match_http(owners, commercial):
    contract = ContractCommercialRelationship(
        engine=owners["cr"]["reader"],
        http=HTTPCommercialRelationship(technical("commercial-relationship", Recorder(refuse))),
    )
    ids = [row["id"] for row in commercial["products"]] + [uuid4(), commercial["products"][0]["id"]]
    expected = run(_cr_double(commercial).presentations_by_products(commercial["company"], ids))
    observed = run(contract.presentations_by_products(commercial["company"], ids))
    assert observed == expected
    assert len(observed) == 5  # cuatro productos de la empresa, el primero con dos presentaciones; la ajena no
    assert {row.status for row in observed} == {"ACTIVE", "INACTIVE"}
    assert run(contract.presentations_by_products(commercial["company"], [])) == []


def test_commercial_api_reads_stay_on_http(commercial):
    """FR-036: `company-products/search` y `applicable-prices/resolve` siguen por API."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/company-products/search"):
            return httpx.Response(200, json={"items": [], "has_more": False})
        return httpx.Response(200, json={"items": []})

    recorder = Recorder(handler)
    contract = ContractCommercialRelationship(
        engine=down_engine("cr"), http=HTTPCommercialRelationship(technical("commercial-relationship", recorder))
    )
    company = commercial["company"]
    assert run(contract.search_products(company, ProductCriteria(), sort_key="display_name", descending=False,
                                        limit=5)) == ([], False)
    assert run(contract.resolve_prices(company, [PriceLine(uuid4(), uuid4(), None)])) == []
    assert len(recorder.requests) == 2


# --------------------------------------------------------------------------- Inventory


@pytest.fixture(scope="module")
def stock(owners):
    company, branch, other_branch = uuid4(), uuid4(), uuid4()
    stocked, emptied, unregistered, never, foreign = (uuid4() for _ in range(5))
    balances = [
        (company, branch, stocked, Decimal("7.5000"), 3),
        (company, branch, emptied, Decimal("0.0000"), 2),
        (company, branch, unregistered, Decimal("0.0000"), 0),
        (company, other_branch, foreign, Decimal("9.0000"), 1),
        (uuid4(), branch, never, Decimal("4.0000"), 1),
    ]
    for owner, place, product, quantity, version in balances:
        insert(owners, "inv", "inventory_balances", company_id=owner, branch_id=place, company_product_id=product,
               quantity=quantity, version=version, **audit(timestamps=False))

    def policy(owner, place, product, minimum, active=True):
        insert(owners, "inv", "inventory_policies", id=uuid4(), company_id=owner, branch_id=place,
               company_product_id=product, minimum_stock=Decimal(minimum), safety_stock_method="BASIC",
               calculation_window_days=90, replenishment_mode="MANUAL", auto_purchase_enabled=False,
               is_active=active, version=1, **audit(timestamps=False))

    policy(company, branch, stocked, "5.5")
    policy(company, branch, emptied, "3", active=False)
    policy(company, other_branch, foreign, "7")
    policy(uuid4(), branch, never, "1")
    return {"company": company, "branch": branch, "balances": balances,
            "products": [stocked, emptied, unregistered, never, foreign],
            "policies": {(company, branch, stocked): "5.5000"}}


def _inv_double(stock: dict) -> HTTPInventory:
    """Inventory con esos datos: un elemento por producto pedido (0 sin saldo) y la política activa o `null`."""

    def handler(request: httpx.Request) -> httpx.Response:
        parts = request.url.path.split("/")
        company, branch = UUID(parts[parts.index("companies") + 1]), UUID(parts[parts.index("branches") + 1])
        ids = list(dict.fromkeys(UUID(value) for value in json.loads(request.content)["company_product_ids"]))
        if request.url.path.endswith("/balances/lookup"):
            rows = {product: (quantity, version) for owner, place, product, quantity, version in stock["balances"]
                    if owner == company and place == branch}
            items = [{"company_id": str(company), "branch_id": str(branch), "company_product_id": str(product),
                      "quantity": str(rows.get(product, (Decimal("0.0000"), 0))[0]),
                      "balance_sequence": rows.get(product, (None, 0))[1], "inventory_value": "0.00",
                      "average_unit_cost": None, "has_unknown_cost": False, "last_movement_at": None}
                     for product in ids]
        else:
            items = [{"company_product_id": str(product),
                      "policy": ({"id": str(uuid4()), "minimum_stock": stock["policies"][(company, branch, product)],
                                  "status": "ACTIVE"} if (company, branch, product) in stock["policies"] else None)}
                     for product in ids]
        return httpx.Response(200, json={"items": items})

    return HTTPInventory(technical("inventory", Recorder(handler)))


def test_balances_match_http(owners, stock):
    contract = ContractInventory(engine=owners["inv"]["reader"],
                                 http=HTTPInventory(technical("inventory", Recorder(refuse))))
    ids = [*stock["products"], uuid4(), stock["products"][0]]
    expected = run(_inv_double(stock).balances(stock["company"], stock["branch"], ids))
    observed = run(contract.balances(stock["company"], stock["branch"], ids))
    assert observed == expected
    assert {str(item.quantity) for item in observed.values()} == {str(item.quantity) for item in expected.values()}
    stocked, emptied, unregistered = stock["products"][:3]
    assert observed[stocked].registered and observed[emptied].registered and not observed[unregistered].registered
    assert run(contract.balances(stock["company"], stock["branch"], [])) == {}


def test_policies_match_http(owners, stock):
    contract = ContractInventory(engine=owners["inv"]["reader"],
                                 http=HTTPInventory(technical("inventory", Recorder(refuse))))
    ids = [*stock["products"], uuid4()]
    expected = run(_inv_double(stock).policies(stock["company"], stock["branch"], ids))
    observed = run(contract.policies(stock["company"], stock["branch"], ids))
    assert observed == expected
    assert list(observed) == [stock["products"][0]]
    assert str(observed[stock["products"][0]].minimum_stock) == "5.5000"


def test_inventory_reads_in_batches_of_100(owners, stock):
    contract = ContractInventory(engine=owners["inv"]["reader"],
                                 http=HTTPInventory(technical("inventory", Recorder(refuse))))
    stocked = stock["products"][0]
    ids = [uuid4() for _ in range(230)] + [stocked]
    balances = run(contract.balances(stock["company"], stock["branch"], ids))
    assert len(balances) == 231 and balances[stocked].quantity == Decimal("7.5000")
    assert list(run(contract.policies(stock["company"], stock["branch"], ids))) == [stocked]


def test_inventory_api_reads_stay_on_http(stock):
    """FR-036: `inventory-product-sets` (conjuntos y pares) e `inventory-summary` siguen por API."""
    counts = {"products_with_positive_balance": 1, "products_with_zero_balance": 0, "products_with_policy": 1,
              "products_below_minimum": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/inventory-summary"):
            return httpx.Response(200, json={"branches": [{"branch_id": str(stock["branch"]), **counts}],
                                             "consolidated": counts})
        return httpx.Response(200, json={"items": [], "has_more": False})

    recorder = Recorder(handler)
    contract = ContractInventory(engine=down_engine("inv"), http=HTTPInventory(technical("inventory", recorder)))
    company, branches = stock["company"], [stock["branch"]]
    assert run(contract.product_set(company, branches, stock_state="IN_STOCK", minimum_state=None, limit=5)) == (
        [], False)
    assert run(contract.below_minimum_pairs(company, branches, limit=5)) == ([], False)
    assert run(contract.summary(company, branches)).consolidated.products_with_policy == 1
    assert len(recorder.requests) == 3


# --------------------------------------------------------------------------- base caída


def test_database_down_is_unavailable():
    engines = {key: down_engine(key) for key in OWNERS}
    company, branch = uuid4(), uuid4()
    try:
        pc = ContractProductCatalog(engine=engines["pc"], http=HTTPProductCatalog(technical("pc", Recorder(refuse))))
        cr = ContractCommercialRelationship(
            engine=engines["cr"], http=HTTPCommercialRelationship(technical("cr", Recorder(refuse))))
        inv = ContractInventory(engine=engines["inv"], http=HTTPInventory(technical("inv", Recorder(refuse))))
        calls = [
            ("product-catalog", "product_summaries", lambda: pc.summaries([uuid4()])),
            ("product-catalog", "units_lookup", lambda: pc.units([uuid4()])),
            ("commercial-relationship", "adopted_count", lambda: cr.count_adopted(company)),
            ("commercial-relationship", "presentations_by_products",
             lambda: cr.presentations_by_products(company, [uuid4()])),
            ("inventory", "balances_lookup", lambda: inv.balances(company, branch, [uuid4()])),
            ("inventory", "policies_lookup", lambda: inv.policies(company, branch, [uuid4()])),
        ]
        for provider, operation, call in calls:
            with pytest.raises(DependencyUnavailableError) as info:
                run(call())
            assert (info.value.provider, info.value.operation) == (provider, operation)
            assert info.value.cause.startswith("contract:")
    finally:
        for engine in engines.values():
            engine.dispose()


# --------------------------------------------------------------------------- selección en dependencies


def test_dependencies_select_source(owners):
    def ports(settings):
        dependencies = build_http_dependencies(settings)
        try:
            return dependencies.ports_factory("Bearer x")
        finally:
            run(dependencies.close())

    default = ports(build_test_settings())
    assert isinstance(default.pc, HTTPProductCatalog)
    assert isinstance(default.cr, HTTPCommercialRelationship)
    assert isinstance(default.inventory, HTTPInventory)

    contract = ports(build_test_settings(
        product_catalog_reads=owners["pc"]["settings"],
        commercial_relationship_reads=owners["cr"]["settings"],
        inventory_reads=owners["inv"]["settings"],
    ))
    assert isinstance(contract.pc, ContractProductCatalog)
    assert isinstance(contract.cr, ContractCommercialRelationship)
    assert isinstance(contract.inventory, ContractInventory)
