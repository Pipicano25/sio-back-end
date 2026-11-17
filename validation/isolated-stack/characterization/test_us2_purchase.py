"""Historia 2: confirmación de una compra de 20 productos distintos (spec 025, T013).

Lo grabado con las lecturas por HTTP debe repetirse igual con las lecturas por contrato. Con ``contract``, la
confirmación no hace **ninguna** solicitud a otros servicios (SC-002) y la recepción solo envía por API la entrada a
Inventory (``inventory-entries``, escritura, FR-031). Las solicitudes de actualización automática de precios las
entrega el worker de Purchase (otro contenedor) y no se cuentan aquí.

Mundo propio de cada ejecución (datos ficticios):

| Dato | Valor |
|---|---|
| Empresa C | activa, COP; admin.test asignado a B1 |
| Proveedor | organización ficticia; condición de contado vigente desde 2026-01-01 y otra vencida (enero de 2026) |
| Productos | P1..P20 adoptados con presentación base, IVA de compra 19 % y cubiertos por una política del 30 % |
| Sin política | P1 y P2 tienen además una caja x12 adoptada sin política (caso "2 líneas sin política") |

"Commercial Relationship caído" se observa en T079 (cierre), que detiene los contenedores de uno en uno: con
``contract`` la confirmación ya no depende del servicio sino de su base.
"""

from __future__ import annotations

import json
import time
from datetime import date
from uuid import uuid4

import pytest
from conftest import URLS, expect, outages_only
from support import Normalizer, RequestWindow, outage_case, owner_database_down, response_case

OC, PC, CR, PI = (URLS[k] for k in ("operational_context", "product_catalog", "commercial_relationship", "party_identity"))
PURCHASE, PR = URLS["purchase"], URLS["payment_reference"]
CONTAINERS = tuple(
    f"sio-it-{name}-service"
    for name in ("purchase", "operational-context", "product-catalog", "commercial-relationship", "party-identity",
                 "payment-reference", "inventory")
)
PRODUCTS = 20
RECEIPT_WITH_CONTRACT = ("/inventory-entries",)
LATENCY = __import__("os").environ.get("SIO_CHARACTERIZATION_LATENCY", "").strip()
LATENCY_SAMPLES = 20


@pytest.fixture(scope="module")
def world(seed, users, run_id):
    admin = users("admin.test")
    colombia = expect(admin.get(f"{URLS['geography']}/global-countries", params={"iso3_code": "COL"}))["items"][0]["id"]
    company = seed.company(admin, colombia, f"US2{run_id}")
    admin_member = seed.member(admin, colombia, company, "admin.test")
    branch = expect(admin.post(f"{OC}/companies/{company}/branches", json={
        "code": f"C1{run_id}", "name": f"Bodega ficticia US2 {run_id}"}))["id"]
    expect(admin.post(f"{OC}/application-users/{admin_member}/user-branches", json={"branch_id": branch}))

    organization = seed.party(admin, colombia, "ORGANIZATION", "NIT", "organization-identities", {
        "country_id": colombia, "identification_type": "NIT",
        "legal_name": f"PROVEEDOR FICTICIO US2 {run_id} (DATO FICTICIO DE VALIDACION)"})
    identification = expect(admin.get(f"{PI}/organization-identities/{organization}"))["identification_number"]
    supplier = expect(admin.post(f"{CR}/companies/{company}/company-suppliers", json={
        "organization_identity_id": organization, "internal_code": f"PRV-{run_id}",
        "display_name": f"Proveedor ficticio US2 {run_id}"}))["id"]
    types = expect(admin.get(f"{PR}/global-payment-condition-types", params={"page_size": 100}))["items"]
    cash_type = next(item["id"] for item in types if item["code"] == "CASH" and item["status"] == "ACTIVE")
    condition = expect(admin.post(f"{CR}/companies/{company}/supplier-payment-conditions", json={
        "company_supplier_id": supplier, "payment_condition_type_id": cash_type, "currency_code": "COP",
        "payment_terms_days": 0, "valid_from": "2026-01-01T00:00:00Z"}))["id"]
    expired = expect(admin.post(f"{CR}/companies/{company}/supplier-payment-conditions", json={
        "company_supplier_id": supplier, "payment_condition_type_id": cash_type, "currency_code": "COP",
        "payment_terms_days": 0, "valid_from": "2026-01-01T00:00:00Z", "valid_to": "2026-02-01T00:00:00Z"}))["id"]
    methods = expect(admin.get(f"{PR}/global-payment-methods", params={"page_size": 100}))["items"]
    cash = next(item["id"] for item in methods if item["code"] == "CASH" and item["status"] == "ACTIVE")

    unit = next(item["id"] for item in expect(admin.get(f"{PC}/units-of-measure", params={"status": "ACTIVE", "page_size": 100}))["items"]
                if item["code"] == "UND")
    category = expect(admin.post(f"{PC}/categories", json={"code": f"US2-{run_id}", "name": f"Categoría US2 (ficticia {run_id})"}))["id"]
    products, uncovered = [], []
    for index in range(1, PRODUCTS + 1):
        product = expect(admin.post(f"{PC}/products", json={
            "product_type": "GOOD", "canonical_name": f"PRODUCTO COMPRA US2 {index} {run_id}", "base_unit_id": unit}))["id"]
        expect(admin.post(f"{PC}/products/{product}/categories", json={"global_category_id": category}))
        presentation = expect(admin.post(f"{PC}/products/{product}/presentations", json={
            "code": f"UND-{index}-{run_id}", "name": "Unidad", "is_base": True}))["id"]
        adopted = expect(admin.post(f"{CR}/companies/{company}/company-products", json={
            "global_product_id": product, "internal_code": f"C-{index}-{run_id}", "display_name": f"Producto compra {index}",
            "currency_code": "COP", "inventory_control_enabled": True}))
        expect(admin.put(f"{CR}/company-products/{adopted['id']}/purchase-tax", json={
            "version": adopted["version"], "purchase_tax_percentage": "19"}))
        row = expect(admin.post(f"{CR}/companies/{company}/company-product-presentations", json={
            "company_product_id": adopted["id"], "global_product_presentation_id": presentation,
            "sku": f"SKU-C{index}-{run_id}"}))
        products.append({"id": adopted["id"], "presentation": row["id"]})
        if index <= 2:
            box = expect(admin.post(f"{PC}/products/{product}/presentations", json={
                "code": f"CJ12-{index}-{run_id}", "name": "Caja x12", "base_quantity": "12", "display_order": 2,
                "is_base": False}))["id"]
            uncovered.append({"id": adopted["id"], "presentation": expect(admin.post(
                f"{CR}/companies/{company}/company-product-presentations", json={
                    "company_product_id": adopted["id"], "global_product_presentation_id": box,
                    "sku": f"SKU-CJ{index}-{run_id}"}))["id"]})
    price_list = expect(admin.post(f"{CR}/companies/{company}/price-lists", json={
        "code": f"COB-{run_id}", "name": f"Lista ficticia de cobertura US2 {run_id}", "currency_code": "COP"}))["id"]
    expect(admin.post(f"{CR}/companies/{company}/price-lists/{price_list}/pricing-policies", json={
        "name": f"Cobertura ficticia US2 {run_id}", "markup_percentage": "30",
        "company_product_presentation_ids": [item["presentation"] for item in products]}))
    expect(admin.post(f"{PURCHASE}/companies/{company}/purchase-sequences", json={
        "series_code": "US2", "prefix": "CP", "separator": "-", "initial_number": 1, "number_length": 6,
        "reset_policy": "NEVER"}))

    aliases = {company: "empresa_C", branch: "B1", admin_member: "admin_C", supplier: "proveedor",
               organization: "organizacion_proveedor", condition: "contado", expired: "contado_vencido", cash: "efectivo",
               cash_type: "tipo_contado", price_list: "lista_cobertura"}
    for index, item in enumerate(products, start=1):
        aliases[item["id"]] = f"P{index}"
        aliases[item["presentation"]] = f"P{index}_UND"
    for index, item in enumerate(uncovered, start=1):
        aliases[item["presentation"]] = f"P{index}_CJ12"
    return {"company": company, "branch": branch, "supplier": supplier, "condition": condition, "expired": expired,
            "cash": cash, "products": products, "uncovered": uncovered, "aliases": aliases, "run": run_id,
            "identification": identification}


def _line(item, index):
    return {"company_product_id": item["id"], "company_product_presentation_id": item["presentation"],
            "quantity": str(index % 3 + 1), "unit_cost": f"{index * 100}.00"}


def _draft(client, world, *, lines=None, condition="condition"):
    items = lines if lines is not None else world["products"]
    return client.post(f"{PURCHASE}/companies/{world['company']}/purchases", json={
        "branch_id": world["branch"], "company_supplier_id": world["supplier"],
        "supplier_payment_condition_id": world[condition], "operation_date": date.today().isoformat(),
        "payment_method_id": world["cash"], "lines": [_line(item, index) for index, item in enumerate(items, start=1)]})


def _confirm(client, world, purchase):
    return client.post(f"{PURCHASE}/companies/{world['company']}/purchases/{purchase['id']}/confirmation",
                       json={"version": purchase["version"]}, headers={"Idempotency-Key": str(uuid4())})


def _receive(client, world, purchase):
    return client.post(f"{PURCHASE}/companies/{world['company']}/purchases/{purchase['id']}/receipt",
                       json={"version": purchase["version"], "full_receipt_confirmed": True},
                       headers={"Idempotency-Key": str(uuid4())})


def _observe(action):
    # Los registros de acceso llegan con retraso: se espera a que salgan los de la preparación anterior.
    time.sleep(1.5)
    window = RequestWindow(CONTAINERS, sources=("sio-it-purchase-service",))
    response = action()
    window.close()
    return response, window.counts()


def _internal(requests):
    """Solicitudes que Purchase hizo a otros servicios (la ventana solo cuenta las que salen de Purchase)."""
    return {key: value for key, value in requests.items() if not key.startswith("purchase ")}


def _check_contract(reads, name, requests, allowed=()):
    if reads != "contract":
        return
    unexpected = {key: value for key, value in _internal(requests).items() if not any(f in key for f in allowed)}
    assert not unexpected, f"{name}: solicitudes a otros servicios con lecturas por contrato: {unexpected}"


def _case(world, response):
    case = response_case(response, Normalizer(world["aliases"], run=world["run"]))
    return json.loads(json.dumps(case, ensure_ascii=False).replace(world["identification"], "<identificacion>"))


def test_success_and_receipt(world, users, book, reads):
    admin = users("admin.test")
    draft = expect(_draft(admin, world), 201)
    confirmed, requests = _observe(lambda: _confirm(admin, world, draft))
    book.check("exito", _case(world, confirmed), requests=requests)
    assert confirmed.status_code == 200, confirmed.text[:300]
    _check_contract(reads, "exito", requests)
    received, receipt_requests = _observe(lambda: _receive(admin, world, confirmed.json()))
    book.check("recepcion", _case(world, received), requests=receipt_requests)
    assert received.status_code == 200, received.text[:300]
    _check_contract(reads, "recepcion", receipt_requests, RECEIPT_WITH_CONTRACT)


def test_two_lines_without_policy(world, users, book, reads):
    admin = users("admin.test")
    draft = expect(_draft(admin, world, lines=world["products"][2:] + world["uncovered"]), 201)
    response, requests = _observe(lambda: _confirm(admin, world, draft))
    book.check("dos_lineas_sin_politica", _case(world, response), requests=requests)
    _check_contract(reads, "dos_lineas_sin_politica", requests)


def test_blocked_supplier(world, users, book, reads):
    admin = users("admin.test")
    draft = expect(_draft(admin, world), 201)
    current = expect(admin.get(f"{CR}/company-suppliers/{world['supplier']}"))
    expect(admin.post(f"{CR}/company-suppliers/{world['supplier']}/block", json={
        "version": current["version"], "block_reason": "Bloqueo ficticio de caracterización"}))
    try:
        response, requests = _observe(lambda: _confirm(admin, world, draft))
        book.check("proveedor_bloqueado", _case(world, response), requests=requests)
        _check_contract(reads, "proveedor_bloqueado", requests)
    finally:
        current = expect(admin.get(f"{CR}/company-suppliers/{world['supplier']}"))
        expect(admin.post(f"{CR}/company-suppliers/{world['supplier']}/unblock", json={"version": current["version"]}))


def test_expired_payment_condition(world, users, book, reads):
    """La vigencia se valida al registrar el borrador (la confirmación repite la misma validación)."""
    admin = users("admin.test")
    response, requests = _observe(lambda: _draft(admin, world, condition="expired"))
    book.check("condicion_vencida", _case(world, response), requests=requests)
    _check_contract(reads, "condicion_vencida", requests)


@pytest.mark.skipif(not LATENCY, reason="Medición opcional: definir SIO_CHARACTERIZATION_LATENCY.")
def test_confirmation_latency(world, users, reads):
    """p50 y p99 del lado del cliente de la confirmación de una compra de 20 productos (T056); sin umbrales."""
    import statistics
    from pathlib import Path

    admin = users("admin.test")
    samples = []
    for index in range(LATENCY_SAMPLES + 3):
        draft = expect(_draft(admin, world), 201)
        started = time.perf_counter()
        response = _confirm(admin, world, draft)
        elapsed = (time.perf_counter() - started) * 1000
        assert response.status_code == 200, response.text[:300]
        if index >= 3:  # calentamiento
            samples.append(elapsed)
    ordered = sorted(samples)
    result = {"operation": "purchase_confirmation_20_lines", "reads": reads, "samples": len(samples),
              "p50_ms": round(statistics.median(samples), 2),
              "p99_ms": round(ordered[min(len(ordered) - 1, int(round(0.99 * (len(ordered) - 1))))], 2)}
    path = Path(LATENCY)
    existing = json.loads(path.read_text()) if path.exists() else []
    path.write_text(json.dumps([*existing, result], indent=2))


PURCHASE_OWNERS = ("operational-context", "product-catalog", "commercial-relationship", "party-identity",
                   "payment-reference", "inventory")


@outages_only
@pytest.mark.parametrize("owner", PURCHASE_OWNERS)
def test_caida_del_propietario(world, users, outage_book, owner):
    """T079: con la base del propietario caída, la confirmación (o la recepción, si es Inventory) responde el 503 de
    hoy, a tiempo y sin efectos; al volver la base, la misma compra avanza."""
    admin = users("admin.test")
    purchase = expect(_draft(admin, world), 201)
    step = _confirm
    if owner == "inventory":
        purchase, step = expect(_confirm(admin, world, purchase)), _receive
    with owner_database_down(owner):
        start = time.monotonic()
        response = step(admin, world, purchase)
        elapsed = time.monotonic() - start
    current = expect(admin.get(f"{PURCHASE}/companies/{world['company']}/purchases/{purchase['id']}"))
    effects = {"estado": current["status"], "recepcion": current.get("receipt_status"),
               "version_cambio": current["version"] != purchase["version"]}
    outage_book.check(owner, outage_case(response, Normalizer(world["aliases"], run=world["run"]), elapsed, 5.5, effects))
    if owner != "inventory":  # la recepción con Inventory caído queda pendiente para el conciliador, como la venta
        expect(step(admin, world, current), 200)
