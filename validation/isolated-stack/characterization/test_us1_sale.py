"""Historia 1: confirmación de una venta de 5 productos (spec 025, T012).

Lo grabado con las lecturas por HTTP debe repetirse igual con las lecturas por contrato. Con ``contract``, durante
la confirmación Sales solo puede pedir a otros servicios ``applicable-prices/resolve`` (precio, FR-031) e
``inventory-outputs`` (escritura, FR-031): ≤ 2 solicitudes internas (SC-001).

Mundo propio de cada ejecución (datos ficticios):

| Dato | Valor |
|---|---|
| Empresa C | activa; miembros admin (B1 asignada) y reportes (sin permiso de confirmar) |
| Sucursales | B1 (admin), B2 (nadie) |
| Productos | P1..P5 adoptados con presentación base, precio en la lista predeterminada y 1000 unidades en B1 |
| Cliente | persona ficticia registrada en la empresa |

La caída de Product Catalog se observa en T079 (cierre), que detiene contenedores de uno en uno.
"""

from __future__ import annotations

import json
import time
from uuid import uuid4

import pytest
from conftest import URLS, expect
from support import Normalizer, RequestWindow, response_case

OC, PC, CR, PI = (URLS[k] for k in ("operational_context", "product_catalog", "commercial_relationship", "party_identity"))
SALES, INV, PR = URLS["sales"], URLS["inventory"], URLS["payment_reference"]
CONTAINERS = tuple(
    f"sio-it-{name}-service"
    for name in ("sales", "operational-context", "product-catalog", "commercial-relationship", "party-identity",
                 "payment-reference", "inventory")
)
ALLOWED_WITH_CONTRACT = ("applicable-prices/resolve", "/inventory-outputs")
STOCK = "1000"
LATENCY = __import__("os").environ.get("SIO_CHARACTERIZATION_LATENCY", "").strip()
LATENCY_SAMPLES = 40


@pytest.fixture(scope="module")
def world(seed, users, run_id, stack_env):
    admin = users("admin.test")
    colombia = expect(admin.get(f"{URLS['geography']}/global-countries", params={"iso3_code": "COL"}))["items"][0]["id"]
    company = seed.company(admin, colombia, f"US1{run_id}")
    admin_member = seed.member(admin, colombia, company, "admin.test")
    seed.member(admin, colombia, company, "reportes.test")
    b1, b2 = (
        expect(admin.post(f"{OC}/companies/{company}/branches", json={
            "code": f"{code}{run_id}", "name": f"Sucursal ficticia {code} {run_id}"}))["id"]
        for code in ("V1", "V2")
    )
    expect(admin.post(f"{OC}/application-users/{admin_member}/user-branches", json={"branch_id": b1}))

    unit = next(item["id"] for item in expect(admin.get(f"{PC}/units-of-measure", params={"status": "ACTIVE", "page_size": 100}))["items"]
                if item["code"] == "UND")
    category = expect(admin.post(f"{PC}/categories", json={"code": f"US1-{run_id}", "name": f"Categoría US1 (ficticia {run_id})"}))["id"]
    price_list = expect(admin.post(f"{CR}/companies/{company}/price-lists", json={
        "code": f"LPV-{run_id}", "name": f"Lista ficticia US1 {run_id}", "currency_code": "COP", "is_default": True}))["id"]

    products = []
    for index in range(1, 6):
        product = expect(admin.post(f"{PC}/products", json={
            "product_type": "GOOD", "canonical_name": f"PRODUCTO VENTA US1 {index} {run_id}", "base_unit_id": unit}))["id"]
        expect(admin.post(f"{PC}/products/{product}/categories", json={"global_category_id": category}))
        presentation = expect(admin.post(f"{PC}/products/{product}/presentations", json={
            "code": f"UND-{index}-{run_id}", "name": "Unidad", "is_base": True}))["id"]
        adopted = expect(admin.post(f"{CR}/companies/{company}/company-products", json={
            "global_product_id": product, "internal_code": f"V-{index}-{run_id}", "display_name": f"Producto venta {index}",
            "currency_code": "COP", "inventory_control_enabled": True}))
        row = expect(admin.post(f"{CR}/companies/{company}/company-product-presentations", json={
            "company_product_id": adopted["id"], "global_product_presentation_id": presentation,
            "sku": f"SKU-V{index}-{run_id}"}))
        expect(admin.post(f"{CR}/companies/{company}/price-list-items", json={
            "price_list_id": price_list, "company_product_id": adopted["id"], "unit_price": f"{index * 1000}.00",
            "company_product_presentation_id": row["id"]}))
        products.append({"id": adopted["id"], "version": adopted["version"], "presentation": row["id"]})

    operator = seed.service(stack_env, "inventory-test-operator", "INVENTORY_TEST_OPERATOR_CLIENT_SECRET")
    expect(operator.post(f"{INV}/inventory-entries", json={
        "operation_key": str(uuid4()), "company_id": company, "branch_id": b1, "origin_type": "PURCHASE",
        "origin_id": str(uuid4()), "application_user_id": admin_member, "correlation_id": str(uuid4()),
        "lines": [{"origin_detail_id": str(uuid4()), "company_product_id": item["id"], "quantity": STOCK,
                   "unit_cost": "700"} for item in products]}))

    person = seed.party(admin, colombia, "PERSON", "CC", "person-identities", {
        "identification_country_id": colombia, "identification_type": "CC",
        "first_name": f"CLIENTEUS1{run_id}", "last_name": "DATO FICTICIO", "birth_date": "1990-01-01"})
    customer = expect(admin.post(f"{CR}/companies/{company}/company-customers", json={
        "customer_kind": "PERSON", "person_identity_id": person, "internal_code": f"CLI-{run_id}",
        "display_name": f"Cliente US1 {run_id} (dato ficticio)"}))["id"]
    identification = expect(admin.get(f"{PI}/person-identities/{person}"))["identification_number"]
    cash = next(item["id"] for item in expect(admin.get(f"{PR}/global-payment-methods", params={"page_size": 100}))["items"]
                if item["code"] == "CASH")
    expect(admin.post(f"{SALES}/companies/{company}/sale-sequences", json={
        "series_code": "US1", "prefix": "FV", "separator": "-", "initial_number": 1, "number_length": 6,
        "reset_policy": "NEVER"}))

    aliases = {company: "empresa_C", b1: "B1", b2: "B2", admin_member: "admin_C", customer: "cliente",
               person: "persona_cliente", cash: "efectivo", price_list: "lista"}
    for index, item in enumerate(products, start=1):
        aliases[item["id"]] = f"P{index}"
        aliases[item["presentation"]] = f"P{index}_UND"
    return {"company": company, "B1": b1, "B2": b2, "customer": customer, "cash": cash, "products": products,
            "aliases": aliases, "run": run_id, "identification": identification}


def _lines(world, quantities):
    return [{"company_product_id": item["id"], "company_product_presentation_id": item["presentation"], "quantity": qty}
            for item, qty in zip(world["products"], quantities, strict=True)]


def _draft(client, world, *, branch="B1", quantities=("1", "2", "1", "3", "1")):
    return client.post(
        f"{SALES}/companies/{world['company']}/sales",
        headers={"Idempotency-Key": str(uuid4())},
        json={"branch_id": world[branch], "company_customer_id": world["customer"], "payment_method_id": world["cash"],
              "lines": _lines(world, quantities)},
    )


def _confirm(client, world, sale):
    return client.post(
        f"{SALES}/companies/{world['company']}/sales/{sale['id']}/confirmation",
        headers={"Idempotency-Key": str(uuid4())},
        json={"version": sale["version"]},
    )


def _observe(world, action):
    # Los registros de acceso llegan con retraso: se espera a que salgan los de la preparación anterior.
    time.sleep(1.5)
    window = RequestWindow(CONTAINERS, sources=("sio-it-sales-service",))
    response = action()
    window.close()
    return response, window.counts()


def _internal(requests):
    """Solicitudes que Sales hizo a otros servicios (la ventana solo cuenta las que salen de Sales; las lecturas
    que Inventory hace por su cuenta al aplicar la salida son de la Historia 5)."""
    return {key: value for key, value in requests.items() if not key.startswith("sales ")}


def _check_contract(reads, name, requests):
    if reads != "contract":
        return
    internal = _internal(requests)
    unexpected = {key: value for key, value in internal.items() if not any(f in key for f in ALLOWED_WITH_CONTRACT)}
    assert not unexpected, f"{name}: lecturas por HTTP con lecturas por contrato: {unexpected}"
    assert sum(internal.values()) <= 2, f"{name}: más de 2 solicitudes internas: {internal}"


def _case(world, response):
    case = response_case(response, Normalizer(world["aliases"], run=world["run"]))
    return json.loads(json.dumps(case, ensure_ascii=False).replace(world["identification"], "<identificacion>"))


def test_success(world, users, book, reads):
    admin = users("admin.test")
    draft, draft_requests = _observe(world, lambda: _draft(admin, world))
    assert draft.status_code == 201, draft.text[:300]
    confirmed, requests = _observe(world, lambda: _confirm(admin, world, draft.json()))
    book.check("borrador", _case(world, draft), requests=draft_requests)
    book.check("exito", _case(world, confirmed), requests=requests)
    assert confirmed.status_code == 200, confirmed.text[:300]
    _check_contract(reads, "exito", requests)
    if reads == "contract":
        assert not _internal(draft_requests) or all(
            any(f in key for f in ALLOWED_WITH_CONTRACT) for key in _internal(draft_requests)
        ), f"borrador: lecturas por HTTP con lecturas por contrato: {draft_requests}"


def test_inactive_product(world, users, book, reads):
    admin = users("admin.test")
    draft = expect(_draft(admin, world), 201)
    target = world["products"][4]
    current = expect(admin.get(f"{CR}/company-products/{target['id']}"))
    expect(admin.post(f"{CR}/company-products/{target['id']}/deactivate", json={"version": current["version"]}))
    try:
        response, requests = _observe(world, lambda: _confirm(admin, world, draft))
        book.check("producto_inactivo", _case(world, response), requests=requests)
        _check_contract(reads, "producto_inactivo", requests)
    finally:
        current = expect(admin.get(f"{CR}/company-products/{target['id']}"))
        expect(admin.post(f"{CR}/company-products/{target['id']}/reactivate", json={"version": current["version"]}))


def test_insufficient_stock(world, users, book, reads):
    admin = users("admin.test")
    draft = expect(_draft(admin, world, quantities=("1", "1", "1", "1", "50000")), 201)
    response, requests = _observe(world, lambda: _confirm(admin, world, draft))
    book.check("existencias_insuficientes", _case(world, response), requests=requests)
    _check_contract(reads, "existencias_insuficientes", requests)


def test_user_without_permission(world, users, book):
    admin, reports = users("admin.test"), users("reportes.test")
    draft = expect(_draft(admin, world), 201)
    response, requests = _observe(world, lambda: _confirm(reports, world, draft))
    book.check("usuario_sin_permiso", _case(world, response), requests=requests)


def test_branch_not_assigned(world, users, book):
    admin = users("admin.test")
    response, requests = _observe(world, lambda: _draft(admin, world, branch="B2"))
    book.check("sucursal_no_asignada", _case(world, response), requests=requests)


@pytest.mark.skipif(not LATENCY, reason="Medición opcional: definir SIO_CHARACTERIZATION_LATENCY.")
def test_confirmation_latency(world, users, reads):
    """p50 y p99 del lado del cliente de la confirmación de una venta de 5 productos (T049); no compara umbrales."""
    import statistics
    from pathlib import Path

    admin = users("admin.test")
    samples = []
    for index in range(LATENCY_SAMPLES + 5):
        draft = expect(_draft(admin, world), 201)
        started = time.perf_counter()
        response = _confirm(admin, world, draft)
        elapsed = (time.perf_counter() - started) * 1000
        assert response.status_code == 200, response.text[:300]
        if index >= 5:  # calentamiento
            samples.append(elapsed)
    ordered = sorted(samples)
    result = {"operation": "sale_confirmation_5_lines", "reads": reads, "samples": len(samples),
              "p50_ms": round(statistics.median(samples), 2),
              "p99_ms": round(ordered[min(len(ordered) - 1, int(round(0.99 * (len(ordered) - 1))))], 2)}
    path = Path(LATENCY)
    existing = json.loads(path.read_text()) if path.exists() else []
    path.write_text(json.dumps([*existing, result], indent=2))
