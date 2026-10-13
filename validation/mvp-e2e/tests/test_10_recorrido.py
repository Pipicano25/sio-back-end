"""Etapa `recorrido`: configuración, compras, inventario, ventas y anulaciones (Historias 1 y 3).

Orden fijo (el archivo se ejecuta de arriba abajo sobre el mismo mundo). Los valores esperados vienen de
`sio_mvp.expected` (data-model §3), nunca del sistema. Si un servicio difiere de su Spec, la prueba
falla y la diferencia se registra como brecha (no se ajusta la aserción).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from scenario import steps as catalogue
from sio_mvp import expected

pytestmark = pytest.mark.e2e

D = Decimal
PLAN = expected.mvp_plan()
PROFITABILITY_FIELDS = ("unit_cost_snapshot", "cost_total", "cost_known", "gross_margin_amount", "gross_margin_percentage")
STATE: dict = {}


def dec(value) -> Decimal:
    return D(str(value))


def check(journal, step_id: str, name: str, expected_value, obtained) -> None:
    ok = journal.verify(step_id, name, expected=expected_value, obtained=obtained)
    assert ok, f"{step_id} {name}: esperado {journal.safe_text(str(expected_value))}, obtenido {journal.safe_text(str(obtained))}"


def run(world, step_id: str, **kwargs):
    return world.run(step_id, **kwargs)


def get(clients, user: str, service: str, path: str, step_id: str, **params):
    response = clients.user(user).get(service, path, step_id=step_id, params=params or None)
    assert response.status == 200, f"{step_id}: GET {path} → {response.status}"
    return response.body


def kardex(clients, world, product: str, step_id: str) -> list[dict]:
    body = get(
        clients, "supervisor.test", "inventory",
        f"/companies/{world['empresa_a']}/branches/{world['sucursal_a1']}/kardex/{world[f'producto_empresa_{product}']}",
        step_id, page_size=100,
    )
    return body["items"]


def balance(clients, world, product: str, step_id: str) -> Decimal:
    body = get(
        clients, "supervisor.test", "inventory",
        f"/companies/{world['empresa_a']}/branches/{world['sucursal_a1']}/balances/{world[f'producto_empresa_{product}']}",
        step_id,
    )
    return dec(body["quantity"])


def open_layers(clients, world, product: str, step_id: str) -> list[tuple[Decimal, Decimal]]:
    body = get(
        clients, "supervisor.test", "inventory",
        f"/companies/{world['empresa_a']}/branches/{world['sucursal_a1']}/valuation/{world[f'producto_empresa_{product}']}/layers",
        step_id, include_closed="true",
    )
    return [(dec(layer["remaining_quantity"]), dec(layer["unit_cost"])) for layer in body["items"] if dec(layer["remaining_quantity"]) > 0]


def delta(movement: dict) -> Decimal:
    return dec(movement["new_balance"]) - dec(movement["previous_balance"])


# --- configuración (C-01..C-13; ítems 1–8) -------------------------------------------------------
@pytest.mark.items(1)
@pytest.mark.evidence("C-01", "C-03")
def test_c03_companies_created_with_cop(world, clients, journal):
    for letter in ("a", "b"):
        company = get(clients, "admin.test", "operational-context", f"/companies/{world[f'empresa_{letter}']}", f"C-03.{letter}")
        check(journal, f"C-03.{letter}", "moneda", "COP", company["default_currency"])
        check(journal, f"C-03.{letter}", "estado", "ACTIVE", company["status"])
        check(journal, f"C-03.{letter}", "organización", world[f"org_empresa_{letter}"], company["organization_identity_id"])


@pytest.mark.items(2)
@pytest.mark.evidence("C-04")
def test_c04_branches_created(world, clients, journal):
    for branch in ("a1", "b1"):
        body = get(clients, "admin.test", "operational-context", f"/branches/{world[f'sucursal_{branch}']}", f"C-04.{branch}")
        check(journal, f"C-04.{branch}", "estado", "ACTIVE", body["status"])
        check(journal, f"C-04.{branch}", "ciudad", world["ciudad"], body["city_id"])


@pytest.mark.items(3)
@pytest.mark.evidence("C-02", "C-05", "C-06", "C-07")
def test_c05_c07_operational_users_and_access(world, journal):
    """Cada usuario de A ve la empresa A y, si está asignado, la sucursal A1 permitida (C-07)."""
    for name, username, letter, branch in catalogue.OPERATIONAL_USERS:
        if letter != "a":
            continue
        response = run(world, f"C-07.{name}")
        memberships = [item for item in response.body["memberships"] if item["company_id"] == world["empresa_a"]]
        check(journal, f"C-07.{name}", f"membresía de {username} en A", 1, len(memberships))
        membership = memberships[0]
        check(journal, f"C-07.{name}", "estado de la membresía", "ACTIVE", membership["status"])
        allowed = {item["branch_id"] for item in membership["branches"] if item["allowed"]}
        expected_branches = {world["sucursal_a1"]} if branch else set()
        check(journal, f"C-07.{name}", "sucursales permitidas", sorted(expected_branches), sorted(allowed))


@pytest.mark.items(4)
@pytest.mark.evidence("C-08")
def test_c08_supplier_with_credit_condition(world, clients, journal):
    supplier = get(clients, "admin.test", "commercial-relationship", f"/company-suppliers/{world['proveedor']}", "C-08.proveedor")
    check(journal, "C-08.proveedor", "estado", "ACTIVE", supplier["status"])
    condition = get(
        clients, "admin.test", "commercial-relationship", f"/supplier-payment-conditions/{world['condicion_credito']}", "C-08.condicion"
    )
    check(journal, "C-08.condicion", "tipo", world["tipo_credito"], condition["payment_condition_type_id"])
    check(journal, "C-08.condicion", "predeterminada", True, condition["is_default"])


@pytest.mark.items(5)
@pytest.mark.evidence("C-09")
def test_c09_person_customer(world, clients, journal):
    customer = get(clients, "admin.test", "commercial-relationship", f"/company-customers/{world['cliente']}", "C-09.cliente")
    check(journal, "C-09.cliente", "tipo", "PERSON", customer["customer_kind"])
    check(journal, "C-09.cliente", "persona", world["persona_cliente"], customer["person_identity_id"])


@pytest.mark.items(6, 7)
@pytest.mark.evidence("C-10", "C-11")
def test_c10_c11_products_adopted_with_presentation(world, clients, journal):
    for letter in ("a", "b"):
        product = get(clients, "admin.test", "commercial-relationship", f"/company-products/{world[f'producto_empresa_{letter}']}", f"C-11.producto_{letter}")
        check(journal, f"C-11.producto_{letter}", "estado", "ACTIVE", product["status"])
        check(journal, f"C-11.producto_{letter}", "control de inventario", True, product["inventory_control_enabled"])
        check(journal, f"C-11.producto_{letter}", "sin precio ni costo (spec 019)", True,
              "sale_price" not in product and "reference_cost" not in product)
        base = get(clients, "admin.test", "commercial-relationship",
                   f"/company-product-presentations/{world[f'presentacion_base_empresa_{letter}']}", f"C-11.base_{letter}")
        check(journal, f"C-11.base_{letter}", "presentación global", world[f"presentacion_base_{letter}"], base["global_product_presentation_id"])
        global_product = get(clients, "admin.test", "product-catalog", f"/products/{world[f'producto_{letter}']}", f"C-10.producto_{letter}")
        assert global_product.get("first_used_at"), f"C-11.producto_{letter}: el producto global no registró su primer uso"
    box = get(clients, "admin.test", "product-catalog", f"/presentations/{world['presentacion_caja_a']}", "C-10.caja_a")
    check(journal, "C-10.caja_a", "base_quantity", D("12"), dec(box["base_quantity"]))
    adopted = get(
        clients, "admin.test", "commercial-relationship", f"/company-product-presentations/{world['presentacion_caja_empresa_a']}", "C-11.caja_a"
    )
    check(journal, "C-11.caja_a", "presentación global", world["presentacion_caja_a"], adopted["global_product_presentation_id"])


@pytest.mark.items(8)
@pytest.mark.evidence("C-11", "C-12", "C-13")
def test_c12_price_lists_and_items(world, clients, journal):
    general = get(clients, "admin.test", "commercial-relationship", f"/price-lists/{world['lista_general']}", "C-12.lista_general")
    check(journal, "C-12.lista_general", "predeterminada", True, general["is_default"])
    mayorista = get(clients, "admin.test", "commercial-relationship", f"/price-lists/{world['lista_mayorista']}", "C-12.lista_mayorista")
    check(journal, "C-12.lista_mayorista", "predeterminada", False, mayorista["is_default"])
    for item, price in (("item_general", "1500.00"), ("item_b", "7000.00"), ("item_mayorista", "16000.00")):
        body = get(clients, "admin.test", "commercial-relationship", f"/price-list-items/{world[item]}", f"C-12.{item}")
        check(journal, f"C-12.{item}", "precio", price, body["unit_price"])
        check(journal, f"C-12.{item}", "moneda", "COP", body["currency_code"])


# --- compras (P-01, P-02; ítems 9–10) -------------------------------------------------------------
@pytest.mark.items(9)
@pytest.mark.evidence("P-01")
def test_p01_register_purchases(world, journal, timer):
    with timer.measure("recorrido.compras"):
        for number in ("1", "2", "3", "4"):
            response = run(world, f"P-01.P{number}")
            body = response.body
            check(journal, f"P-01.P{number}", "estado", "DRAFT", body["status"])
            check(journal, f"P-01.P{number}", "sin número", None, body["number"])
            check(journal, f"P-01.P{number}", "fecha de negocio de A1", world["fecha_negocio"], body["operation_date"])
            check(journal, f"P-01.P{number}", "moneda", "COP", body["currency_code"])
            STATE[f"compra_{number}"] = body
    p1 = STATE["compra_1"]
    box_line = next(line for line in p1["lines"] if line.get("company_product_presentation_id") == world["presentacion_caja_empresa_a"])
    entry = PLAN.entry("P1", "A")
    # DS-04 de la 014: (subtotal − descuento) / (cantidad × factor), sin impuestos.
    check(journal, "P-01.P1", "cantidad base de la línea caja", entry.quantity, dec(box_line["base_quantity"]))
    check(journal, "P-01.P1", "costo por unidad base de la línea caja", entry.unit_cost, dec(box_line["inventory_unit_cost"]))
    check(journal, "P-01.P1", "subtotal de la línea caja", D("24000"), dec(box_line["subtotal"]))


@pytest.mark.items(10)
@pytest.mark.evidence("P-02")
def test_p02_confirm_purchases_once(world, clients, journal, timer):
    with timer.measure("recorrido.compras"):
        for number in ("1", "2", "3"):
            body = run(world, f"P-02.P{number}").body
            check(journal, f"P-02.P{number}", "estado", "CONFIRMED", body["status"])
            assert body["number"], f"P-02.P{number}: la compra confirmada no tiene número oficial"
            assert body["inventory_operation_id"], f"P-02.P{number}: sin operación de Inventory"
            STATE[f"compra_{number}_confirmada"] = body
        # Repetir la confirmación de P1 con la misma clave: misma respuesta, sin segundo movimiento ni número.
        again = world.runner.run(world.step("P-02.P1"), record_audit=False, overrides={"compra_1_version": STATE["compra_1"]["version"]})
        check(journal, "P-02.P1", "repetición: mismo número", STATE["compra_1_confirmada"]["number"], again.body["number"])
        check(journal, "P-02.P1", "repetición: misma operación", STATE["compra_1_confirmada"]["inventory_operation_id"], again.body["inventory_operation_id"])
    entries_p1 = [item for item in kardex(clients, world, "a", "P-02.P1") if item.get("origin_id") == world["compra_1"]]
    check(journal, "P-02.P1", "movimientos de P1 en A tras repetir", 1, len(entries_p1))


# --- inventario tras las compras (P-03; ítems 11, 12, 18) --------------------------------------------
@pytest.mark.items(11, 12, 18)
@pytest.mark.evidence("P-03")
def test_p03_inventory_after_purchases(world, journal):
    snapshot = PLAN.snapshot("compras")
    for product in ("a", "b"):
        body = run(world, f"P-03.saldo_{product}").body
        check(journal, f"P-03.saldo_{product}", "saldo", snapshot.quantity(product.upper()), dec(body["quantity"]))
    for product in ("a", "b"):
        layers = run(world, f"P-03.capas_{product}").body["items"]
        obtained = [(dec(layer["remaining_quantity"]), dec(layer["unit_cost"])) for layer in layers if dec(layer["remaining_quantity"]) > 0]
        wanted = [(layer.remaining, layer.unit_cost) for layer in snapshot.layers(product.upper())]
        check(journal, f"P-03.capas_{product}", "capas FIFO", wanted, obtained)
        value = sum((quantity * cost for quantity, cost in obtained), D("0"))
        check(journal, f"P-03.capas_{product}", "valor", snapshot.value(product.upper()), value)
    movements = run(world, "P-03.kardex_a").body["items"]
    wanted = [(quantity, origin) for _, quantity, origin in PLAN.kardex("A")[:3]]
    origins = {world["compra_1"]: "P1", world["compra_2"]: "P2", world["compra_3"]: "P3"}
    obtained = [(delta(item), origins.get(item.get("origin_id"), "?")) for item in movements]
    check(journal, "P-03.kardex_a", "entradas con documento de origen", wanted, obtained)
    for item in movements:
        assert item.get("origin_type") == "PURCHASE", "P-03.kardex_a: la entrada no referencia la compra de origen"


# --- ventas (V-01..V-07; ítems 13–18) -----------------------------------------------------------------
@pytest.mark.items(13)
@pytest.mark.evidence("V-01")
def test_v01_register_sales_with_presentation_prices(world, journal, timer):
    with timer.measure("recorrido.ventas"):
        for number in ("1", "2", "3", "4", "5", "6", "7"):
            body = run(world, f"V-01.V{number}").body
            check(journal, f"V-01.V{number}", "estado", "DRAFT", body["status"])
            STATE[f"venta_{number}"] = body
    v1, v2, v3 = (STATE[f"venta_{number}"]["lines"][0] for number in ("1", "2", "3"))
    check(journal, "V-01.V1", "precio (lista indicada MAYORISTA)", D("16000"), dec(v1["unit_price"]))
    check(journal, "V-01.V1", "ítem de lista", world["item_mayorista"], v1["price_list_item_id"])
    check(journal, "V-01.V1", "lista pedida explícitamente", True, v1["price_list_requested"])
    check(journal, "V-01.V2", "precio (lista predeterminada GENERAL)", D("1500"), dec(v2["unit_price"]))
    check(journal, "V-01.V2", "lista resuelta", world["lista_general"], v2["price_list_id"])
    check(journal, "V-01.V2", "lista no pedida", False, v2["price_list_requested"])
    check(journal, "V-01.V3", "precio (unidad de B en GENERAL)", D("7000"), dec(v3["unit_price"]))
    check(journal, "V-01.V3", "origen del precio", "PRICE_LIST_ITEM", v3["price_source"])
    check(journal, "V-01.V3", "ítem de lista", world["item_b"], v3["price_list_item_id"])
    check(journal, "V-01.V1", "origen del precio", "PRICE_LIST_ITEM", v1["price_source"])


@pytest.mark.items(14)
@pytest.mark.evidence("V-02")
def test_v02_availability_before_confirmation(world, journal):
    v2 = run(world, "V-02.V2").body
    check(journal, "V-02.V2", "disponible", True, v2["all_available"])
    check(journal, "V-02.V2", "cantidad base requerida", D("20"), dec(v2["products"][0]["required_base_quantity"]))
    v4 = run(world, "V-02.V4").body
    check(journal, "V-02.V4", "disponible", False, v4["all_available"])
    check(journal, "V-02.V4", "cantidad base requerida", D("100"), dec(v4["products"][0]["required_base_quantity"]))


@pytest.mark.items(15)
@pytest.mark.evidence("V-03")
def test_v03_confirm_sales_once(world, clients, journal, timer):
    with timer.measure("recorrido.ventas"):
        for number in ("1", "2", "3"):
            body = run(world, f"V-03.V{number}").body
            check(journal, f"V-03.V{number}", "estado", "CONFIRMED", body["status"])
            assert body["number"], f"V-03.V{number}: la venta confirmada no tiene número"
            line = body["lines"][0]
            original = STATE[f"venta_{number}"]["lines"][0]
            check(journal, f"V-03.V{number}", "precio conservado", dec(original["unit_price"]), dec(line["unit_price"]))
            check(journal, f"V-03.V{number}", "origen conservado", original["price_source"], line["price_source"])
            STATE[f"venta_{number}_confirmada"] = body
        again = world.runner.run(world.step("V-03.V1"), record_audit=False, overrides={"venta_1_version": STATE["venta_1"]["version"]})
        check(journal, "V-03.V1", "repetición: mismo número", STATE["venta_1_confirmada"]["number"], again.body["number"])
    outputs_v1 = [item for item in kardex(clients, world, "a", "V-03.V1") if item.get("origin_id") == world["venta_1"]]
    check(journal, "V-03.V1", "salidas de V1 tras repetir", 1, len(outputs_v1))


@pytest.mark.items(14)
@pytest.mark.evidence("V-04")
def test_v04_insufficient_stock_rejected(world, clients, journal):
    before = balance(clients, world, "a", "V-04.V4")
    rejected = run(world, "V-04.V4")
    check(journal, "V-04.V4", "código", "SALES.INSUFFICIENT_STOCK", rejected.body.get("code"))
    current = get(clients, "ventas.test", "sales", f"/companies/{world['empresa_a']}/sales/{world['venta_4']}", "V-04.V4")
    check(journal, "V-04.V4", "estado", "DRAFT", current["status"])
    check(journal, "V-04.V4", "sin número", None, current["number"])
    check(journal, "V-04.V4", "saldo sin cambios", before, balance(clients, world, "a", "V-04.V4"))


@pytest.mark.items(15)
@pytest.mark.evidence("V-05", "V-05b")
def test_v05_prices_changed_and_inactive_product(world, clients, journal):
    before_a = balance(clients, world, "a", "V-05.V5")
    run(world, "V-05.cambio")
    rejected = run(world, "V-05.V5")
    check(journal, "V-05.V5", "código", "SALES.PRICES_CHANGED", rejected.body.get("code"))
    current = get(clients, "ventas.test", "sales", f"/companies/{world['empresa_a']}/sales/{world['venta_5']}", "V-05.V5")
    check(journal, "V-05.V5", "estado", "DRAFT", current["status"])
    check(journal, "V-05.V5", "sin número", None, current["number"])
    check(journal, "V-05.V5", "saldo sin cambios", before_a, balance(clients, world, "a", "V-05.V5"))
    # V-05b: producto de empresa B inactivo antes de confirmar V7.
    before_b = balance(clients, world, "b", "V-05b.V7")
    run(world, "V-05b.inactivar")
    world.vars["venta_7_version"] = current_version(clients, world, "7")
    rejected = run(world, "V-05b.V7")
    check(journal, "V-05b.V7", "código", "SALES.REFERENCES_NOT_ELIGIBLE", rejected.body.get("code"))
    v7 = get(clients, "ventas.test", "sales", f"/companies/{world['empresa_a']}/sales/{world['venta_7']}", "V-05b.V7")
    check(journal, "V-05b.V7", "estado", "DRAFT", v7["status"])
    check(journal, "V-05b.V7", "sin número", None, v7["number"])
    check(journal, "V-05b.V7", "saldo sin cambios", before_b, balance(clients, world, "b", "V-05b.V7"))
    reactivated = run(world, "V-05b.reactivar").body
    check(journal, "V-05b.reactivar", "producto B activo", "ACTIVE", reactivated["status"])


def current_version(clients, world, number: str) -> int:
    body = get(clients, "ventas.test", "sales", f"/companies/{world['empresa_a']}/sales/{world[f'venta_{number}']}", f"V-version.V{number}")
    return body["version"]


@pytest.mark.items(16, 17, 18)
@pytest.mark.evidence("V-06", "V-07")
def test_v06_v07_cost_margin_and_outputs(world, clients, journal):
    seller = run(world, "V-06.vendedor").body
    for field in PROFITABILITY_FIELDS:
        assert field not in seller["lines"][0], f"V-06.vendedor: ventas.test recibe {field}"
    assert "has_unknown_cost" not in seller, "V-06.vendedor: ventas.test recibe has_unknown_cost"
    supervisor = run(world, "V-06.supervisor").body
    output = PLAN.output("V2")
    line = supervisor["lines"][0]
    check(journal, "V-06.supervisor", "costo V2", output.cost, dec(line["cost_total"]))
    check(journal, "V-06.supervisor", "margen V2", output.margin, dec(line["gross_margin_amount"]))
    check(journal, "V-06.supervisor", "margen % V2", output.margin_percent, dec(line["gross_margin_percentage"]).quantize(D("0.01")))
    for number in ("1", "3"):
        body = get(clients, "supervisor.test", "sales", f"/companies/{world['empresa_a']}/sales/{world[f'venta_{number}']}", "V-06.supervisor")
        planned = PLAN.output(f"V{number}")
        check(journal, "V-06.supervisor", f"costo V{number}", planned.cost, dec(body["lines"][0]["cost_total"]))
        check(journal, "V-06.supervisor", f"margen V{number}", planned.margin, dec(body["lines"][0]["gross_margin_amount"]))
    snapshot = PLAN.snapshot("ventas")
    for product in ("a", "b"):
        body = run(world, f"V-07.saldo_{product}").body
        check(journal, f"V-07.saldo_{product}", "saldo tras ventas", snapshot.quantity(product.upper()), dec(body["quantity"]))
        layers = run(world, f"V-07.capas_{product}").body["items"]
        obtained = [(dec(layer["remaining_quantity"]), dec(layer["unit_cost"])) for layer in layers if dec(layer["remaining_quantity"]) > 0]
        check(journal, f"V-07.capas_{product}", "capas abiertas", [(l.remaining, l.unit_cost) for l in snapshot.layers(product.upper()) if l.remaining], obtained)
    movements_a = run(world, "V-07.kardex_a").body["items"]
    movements_b = run(world, "V-07.kardex_b").body["items"]
    sale_origin = {world["venta_1"]: "v1", world["venta_2"]: "v2", world["venta_3"]: "v3"}
    for item in movements_a + movements_b:
        name = sale_origin.get(item.get("origin_id"))
        if name:
            world.vars[f"movimiento_{name}"] = item["id"]
    for name in ("v1", "v2", "v3"):
        consumptions = run(world, f"V-07.consumos_{name}").body["items"]
        planned = PLAN.output(name.upper())
        check(
            journal, f"V-07.consumos_{name}", "consumos FIFO",
            [(item.quantity, item.unit_cost) for item in planned.consumptions],
            [(dec(item["quantity"]), dec(item["unit_cost"])) for item in consumptions],
        )
        check(journal, f"V-07.consumos_{name}", "costo", planned.cost, sum((dec(item["cost_amount"]) for item in consumptions), D("0")))


# --- anulaciones (A-01..A-03; ítems 17, 18, 20) --------------------------------------------------------
@pytest.mark.items(20)
@pytest.mark.evidence("A-01")
def test_a01_cancellations_and_reversals(world, clients, journal, timer):
    with timer.measure("recorrido.anulaciones"):
        world.vars["compra_4_version"] = STATE["compra_4"]["version"]
        p4 = run(world, "A-01.P4").body
        check(journal, "A-01.P4", "estado", "CANCELLED", p4["status"])
        check(journal, "A-01.P4", "sin número", None, p4["number"])
        world.vars["venta_6_version"] = current_version(clients, world, "6")
        v6 = run(world, "A-01.V6").body
        check(journal, "A-01.V6", "estado", "CANCELLED", v6["status"])
        v3 = run(world, "A-01.V3").body
        check(journal, "A-01.V3", "estado", "CANCELLED", v3["status"])
        check(journal, "A-01.V3", "número conservado", STATE["venta_3_confirmada"]["number"], v3["number"])
        check(journal, "A-01.V3", "saldo B tras el reverso", PLAN.snapshot("final").quantity("B"), balance(clients, world, "b", "A-01.V3"))
        p3 = run(world, "A-01.P3").body
        check(journal, "A-01.P3", "estado", "CANCELLED", p3["status"])
        check(journal, "A-01.P3", "número conservado", STATE["compra_3_confirmada"]["number"], p3["number"])
        check(journal, "A-01.P3", "saldo A tras el reverso", PLAN.snapshot("final").quantity("A"), balance(clients, world, "a", "A-01.P3"))
    # Operaciones de reverso de Inventory (auditoría esperada REVERSE_INVENTORY_*).
    for kind, number, action, letter in (("venta", "3", "REVERSE_INVENTORY_OUTPUT", "V"), ("compra", "3", "REVERSE_INVENTORY_ENTRY", "P")):
        step = world.step(f"A-01.operaciones_{letter}{number}")
        operations = world.runner.run(step).body
        items = operations if isinstance(operations, list) else operations.get("items", [])
        cancel = [item for item in items if item.get("operation_type") == "CANCEL" and item.get("status") == "SUCCEEDED"]
        assert len(cancel) == 1, f"{step.id}: se esperaba una operación de anulación completada, hay {len(cancel)}"
        reversal = cancel[0]["inventory_operation_id"]
        world.vars[f"{kind}_{number}_reverso"] = reversal
        from scenario.steps import AuditSpec

        world.runner.expect_audit(
            world.step(f"A-01.{letter}{number}"),
            AuditSpec("inventory", action, "InventoryOperation", f"{{{kind}_{number}_reverso}}", correlated=True),
            world.runner.context.correlation_id(f"A-01.{letter}{number}"),
        )


@pytest.mark.items(20)
@pytest.mark.evidence("A-02")
def test_a02_cancel_consumed_purchase_rejected(world, clients, journal):
    before = balance(clients, world, "a", "A-02.P1")
    world.vars["compra_1_version"] = get(
        clients, "compras.test", "purchase", f"/companies/{world['empresa_a']}/purchases/{world['compra_1']}", "A-02.P1"
    )["version"]
    rejected = run(world, "A-02.P1")
    check(journal, "A-02.P1", "código", "PURCHASE.INVENTORY_ALREADY_CONSUMED", rejected.body.get("code"))
    current = get(clients, "compras.test", "purchase", f"/companies/{world['empresa_a']}/purchases/{world['compra_1']}", "A-02.P1")
    check(journal, "A-02.P1", "estado", "CONFIRMED", current["status"])
    check(journal, "A-02.P1", "saldo sin cambios", before, balance(clients, world, "a", "A-02.P1"))


@pytest.mark.items(17, 18, 20)
@pytest.mark.evidence("A-03")
def test_a03_final_inventory(world, journal):
    final = PLAN.snapshot("final")
    for product in ("a", "b"):
        body = run(world, f"A-03.saldo_{product}").body
        check(journal, f"A-03.saldo_{product}", "saldo final", final.quantity(product.upper()), dec(body["quantity"]))
        layers = run(world, f"A-03.capas_{product}").body["items"]
        obtained = [(dec(layer["remaining_quantity"]), dec(layer["unit_cost"])) for layer in layers if dec(layer["remaining_quantity"]) > 0]
        check(journal, f"A-03.capas_{product}", "capas abiertas finales", [(l.remaining, l.unit_cost) for l in final.layers(product.upper()) if l.remaining], obtained)
    valuation = run(world, "A-03.valoracion").body["items"]
    values = {item["company_product_id"]: dec(item["inventory_value"]) for item in valuation}
    check(journal, "A-03.valoracion", "valor final A", final.value("A"), values.get(world["producto_empresa_a"]))
    check(journal, "A-03.valoracion", "valor final B", final.value("B"), values.get(world["producto_empresa_b"]))
    origins = {
        world["compra_1"]: "P1", world["compra_2"]: "P2", world["compra_3"]: "P3",
        world["venta_1"]: "V1", world["venta_2"]: "V2", world["venta_3"]: "V3",
    }
    for product in ("a", "b"):
        movements = run(world, f"A-03.kardex_{product}").body["items"]
        obtained = [(delta(item), origins.get(item.get("origin_id"), "?")) for item in movements]
        wanted = [(quantity, origin) for _, quantity, origin in PLAN.kardex(product.upper())]
        check(journal, f"A-03.kardex_{product}", "kardex final con signo y origen", wanted, obtained)
        sequences = [item["balance_sequence"] for item in movements]
        check(journal, f"A-03.kardex_{product}", "secuencia sin huecos", list(range(sequences[0], sequences[0] + len(sequences))), sequences)
        check(journal, f"A-03.kardex_{product}", "saldos acumulados", PLAN.running_balances(product.upper()), [dec(item["new_balance"]) for item in movements])
