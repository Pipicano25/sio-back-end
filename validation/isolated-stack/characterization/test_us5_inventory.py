"""Historia 5: salidas, entradas y ajustes de inventario (spec 025, T016).

Lo grabado con las lecturas por HTTP debe repetirse igual con las lecturas por contrato. Con ``contract``, Inventory
no hace **ninguna** solicitud a Operational Context ni a Commercial Relationship para validar la sucursal, el usuario,
la moneda y los productos (SC-005).

Mundo propio de cada ejecución (datos ficticios): una empresa con ``admin.test`` asignado a la sucursal ``B1``, una
sucursal ``B2`` inactiva, un producto con control de inventario (``P1``) y otro sin él (``P2``), y existencias de
``P1`` en ``B1`` cargadas por la cuenta técnica ``inventory-test-operator``. Casos:

- salida válida (cuenta técnica);
- salida con la sucursal inactiva, un usuario inexistente y un producto ajeno a la vez: el ``422`` conserva el orden
  de los errores (sucursal, usuario, productos);
- salida de un producto sin control de inventario;
- entrada (valida además la moneda de la empresa);
- ajuste positivo de ``admin.test`` (acceso operativo, producto y moneda).

La moneda inexistente no se puede provocar en la pila (toda empresa tiene una); la cubren las pruebas de
``INV/tests/contract_reads/test_inventory_reads.py``.
"""

from __future__ import annotations

import json
import time
from uuid import uuid4

import pytest
from conftest import URLS, expect
from support import Normalizer, RequestWindow, response_case

OC, PC, CR, INV = (URLS[k] for k in ("operational_context", "product_catalog", "commercial_relationship", "inventory"))
CONTAINERS = tuple(f"sio-it-{name}-service" for name in ("inventory", "operational-context", "commercial-relationship"))
STOCK = "50"


@pytest.fixture(scope="module")
def world(seed, users, run_id, stack_env):
    admin = users("admin.test")
    colombia = expect(admin.get(f"{URLS['geography']}/global-countries", params={"iso3_code": "COL"}))["items"][0]["id"]
    company = seed.company(admin, colombia, f"US5{run_id}")
    member = seed.member(admin, colombia, company, "admin.test")
    b1, b2 = (
        expect(admin.post(f"{OC}/companies/{company}/branches", json={
            "code": f"{code}{run_id}", "name": f"Sucursal ficticia {code} {run_id}"}))
        for code in ("I1", "I2")
    )
    expect(admin.post(f"{OC}/application-users/{member}/user-branches", json={"branch_id": b1["id"]}))
    expect(admin.post(f"{OC}/branches/{b2['id']}/deactivate", json={"version": b2["version"]}))

    unit = next(item["id"] for item in expect(admin.get(f"{PC}/units-of-measure", params={"status": "ACTIVE", "page_size": 100}))["items"]
                if item["code"] == "UND")
    category = expect(admin.post(f"{PC}/categories", json={"code": f"US5-{run_id}", "name": f"Categoría US5 (ficticia {run_id})"}))["id"]
    products = []
    for index, control in ((1, True), (2, False)):
        product = expect(admin.post(f"{PC}/products", json={
            "product_type": "GOOD", "canonical_name": f"PRODUCTO INVENTARIO US5 {index} {run_id}", "base_unit_id": unit}))["id"]
        expect(admin.post(f"{PC}/products/{product}/categories", json={"global_category_id": category}))
        expect(admin.post(f"{PC}/products/{product}/presentations", json={
            "code": f"UND-{index}-{run_id}", "name": "Unidad", "is_base": True}))
        products.append(expect(admin.post(f"{CR}/companies/{company}/company-products", json={
            "global_product_id": product, "internal_code": f"I-{index}-{run_id}", "display_name": f"Producto inventario {index}",
            "currency_code": "COP", "inventory_control_enabled": control}))["id"])

    operator = seed.service(stack_env, "inventory-test-operator", "INVENTORY_TEST_OPERATOR_CLIENT_SECRET")
    world = {"company": company, "B1": b1["id"], "B2": b2["id"], "member": member, "P1": products[0],
             "P2": products[1], "operator": operator, "run": run_id}
    expect(_operation(world, "inventory-entries", lines=[(products[0], STOCK, "700")]))
    world["aliases"] = {company: "empresa", b1["id"]: "B1", b2["id"]: "B2", member: "admin", products[0]: "P1",
                        products[1]: "P2"}
    return world


def _operation(world, path, *, branch="B1", user=None, lines):
    body = {"operation_key": str(uuid4()), "company_id": world["company"], "branch_id": world[branch],
            "origin_type": "PURCHASE" if path == "inventory-entries" else "SALE", "origin_id": str(uuid4()),
            "application_user_id": user or world["member"], "correlation_id": str(uuid4()),
            "lines": [{"origin_detail_id": str(uuid4()), "company_product_id": product, "quantity": quantity,
                       **({"unit_cost": cost} if cost else {})} for product, quantity, cost in lines]}
    return world["operator"].post(f"{INV}/{path}", json=body)


def _observe(action):
    # Los registros de acceso llegan con retraso: se espera a que salgan los de la preparación anterior.
    time.sleep(1.5)
    window = RequestWindow(CONTAINERS, sources=("sio-it-inventory-service",))
    response = action()
    window.close()
    return response, window.counts()


def _internal(requests):
    """Solicitudes que Inventory hizo a otros servicios (la ventana solo cuenta las que salen de Inventory)."""
    return {key: value for key, value in requests.items() if not key.startswith("inventory ")}


def _check(world, book, reads, name, response, requests, status):
    assert response.status_code == status, f"{name}: {response.status_code} {response.text[:300]}"
    case = response_case(response, Normalizer(world["aliases"], run=world["run"]))
    book.check(name, json.loads(json.dumps(case, ensure_ascii=False)), requests=requests)
    if reads == "contract":
        assert not _internal(requests), f"{name}: solicitudes a otros servicios con contract: {_internal(requests)}"
    return case


def test_salida_valida(world, book, reads):
    response, requests = _observe(lambda: _operation(world, "inventory-outputs", lines=[(world["P1"], "3", None)]))
    _check(world, book, reads, "salida_valida", response, requests, 201)


def test_salida_con_errores_en_orden(world, book, reads):
    """Sucursal inactiva, usuario inexistente y producto ajeno a la vez: un solo 422 con los errores en orden."""
    response, requests = _observe(lambda: _operation(
        world, "inventory-outputs", branch="B2", user=str(uuid4()), lines=[(world["P1"], "1", None), (str(uuid4()), "1", None)]))
    case = _check(world, book, reads, "salida_errores_en_orden", response, requests, 422)
    codes = [item.get("code") for item in case["body"].get("errors", [])]
    assert codes[:2] == ["BRANCH_INACTIVE", "APPLICATION_USER_NOT_FOUND"], codes


def test_salida_producto_sin_control(world, book, reads):
    response, requests = _observe(lambda: _operation(world, "inventory-outputs", lines=[(world["P2"], "1", None)]))
    _check(world, book, reads, "salida_producto_sin_control", response, requests, 422)


def test_entrada(world, book, reads):
    response, requests = _observe(lambda: _operation(world, "inventory-entries", lines=[(world["P1"], "5", "800")]))
    _check(world, book, reads, "entrada", response, requests, 201)


def test_ajuste(world, users, book, reads):
    admin = users("admin.test")
    response, requests = _observe(lambda: admin.post(f"{INV}/companies/{world['company']}/inventory-adjustments", json={
        "adjustment_key": str(uuid4()), "branch_id": world["B1"], "company_product_id": world["P1"],
        "adjustment_type": "POSITIVE", "quantity": "2", "unit_cost": "750",
        "reason": f"Ajuste ficticio de validación {world['run']}"}))
    _check(world, book, reads, "ajuste", response, requests, 201)
