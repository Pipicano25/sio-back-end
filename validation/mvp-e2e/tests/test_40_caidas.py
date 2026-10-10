"""Etapa `caidas`: dependencias no disponibles (Historia 5; ítem 22; FR-017, FR-018; research R-09).

Casos en serie y nunca dos dependencias detenidas a la vez: O1, O2, O3, O4a, O4b, O5, O6. Cada caso
tiene datos propios (`O{n}-{RUN_ID}`) sobre la empresa A, consulta el estado antes, detiene **un**
contenedor con `docker stop`, hace la petición durante la caída, comprueba la ausencia de efectos y
restaura por completo (contenedor en ejecución, `/health/ready` = 200 y una lectura autenticada que use
la dependencia) antes del caso siguiente. Si una restauración falla, los casos restantes quedan
BLOQUEADO. O2 espera el umbral real del conciliador de Sales, sin tocar la base (P-03). Las lecturas de
outbox son `SELECT` por `docker exec … psql` (solo lectura).
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from sio_mvp.audit_check import AuditChecker, HttpAuditSource
from scenario.steps import OPERATIONAL_USERS
from sio_mvp.journal import ExpectedAudit

pytestmark = [pytest.mark.outage]

D = Decimal
STATE: dict = {"blocked": None, "outages": []}
RECONCILER_MARGIN_SECONDS = 120.0


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def write_outages(report_dir) -> None:
    (report_dir / "outages.json").write_text(json.dumps(STATE["outages"], ensure_ascii=False, indent=2), encoding="utf-8")


@pytest.fixture(autouse=True)
def serial_guard(report_dir):
    if STATE["blocked"]:
        pytest.skip(f"BLOQUEADO: no se restauró {STATE['blocked']} en un caso anterior")
    yield
    write_outages(report_dir)


@pytest.fixture(scope="module")
def case_env(world, clients, docker, settings, journal, realm, report_dir):
    if "producto_empresa_a" not in world.vars:
        pytest.skip("BLOQUEADO: la etapa caidas necesita la configuración del recorrido")
    return {"world": world, "clients": clients, "docker": docker, "settings": settings, "journal": journal, "realm": realm}


class Case:
    """Registro de un caso para outages.json; siempre se escribe, aunque el caso falle."""

    def __init__(self, name: str, container: str) -> None:
        self.data = {"case": name, "container": container, "restored": False}
        STATE["outages"].append(self.data)

    def __setitem__(self, key, value):
        self.data[key] = value


def run_outage(case: Case, docker, container: str, health, body):
    """Detiene un contenedor, ejecuta `body()` y restaura; registra tiempos y restauración."""
    case["outage_started_at"] = now_iso()
    started = time.monotonic()
    try:
        with docker.stopped(container, health=health):
            body()
            case["outage_finished_at"] = now_iso()
            restore_started = time.monotonic()
    except Exception:
        state = docker.inspect(container)
        if state.status != "running":
            STATE["blocked"] = container
        case["restored"] = state.healthy
        raise
    case["restored"] = True
    case["seconds_to_health"] = round(time.monotonic() - restore_started, 1)
    case["outage_seconds"] = round(time.monotonic() - started, 1)


def http_ok(clients, user, service, path, step_id) -> bool:
    return clients.user(user).get(service, path, step_id=step_id).status == 200


def ready(clients, service: str) -> bool:
    return clients.anonymous().get(service, "/health/ready", step_id="restauracion", root=True).status == 200


def purchase_body(world, label: str, quantity: str, unit_cost: str) -> dict:
    return {
        "branch_id": world["sucursal_a1"],
        "company_supplier_id": world["proveedor"],
        "operation_date": world["fecha_negocio"],
        "supplier_document_number": f"{label}-{world['run']}",
        "lines": [{"company_product_id": world["producto_empresa_a"], "quantity": quantity, "unit_cost": unit_cost}],
    }


def sale_body(world) -> dict:
    return {"branch_id": world["sucursal_a1"], "company_customer_id": world["cliente"], "lines": [{"company_product_id": world["producto_empresa_a"], "quantity": "1"}]}


def balance_a(clients, world, step_id) -> Decimal:
    response = clients.user("supervisor.test").get(
        "inventory", f"/companies/{world['empresa_a']}/branches/{world['sucursal_a1']}/balances/{world['producto_empresa_a']}", step_id=step_id
    )
    assert response.status == 200, f"{step_id}: saldo → {response.status}"
    return D(response.body["quantity"])


def movements_for(clients, world, origin_id, step_id) -> list[dict]:
    response = clients.user("supervisor.test").get(
        "inventory",
        f"/companies/{world['empresa_a']}/branches/{world['sucursal_a1']}/kardex/{world['producto_empresa_a']}",
        step_id=step_id,
        params={"origin_id": origin_id, "page_size": 100},
    )
    assert response.status == 200
    return response.body["items"]


def by_key(clients, world, operation_key, step_id) -> int:
    response = clients.user("supervisor.test").get(
        "inventory", f"/companies/{world['empresa_a']}/inventory-operations/by-key/{operation_key}", step_id=step_id
    )
    return response.status


def audit_once(env, expectations: list[ExpectedAudit]) -> None:
    subjects = {name: user["id"] for name, user in env["realm"].users.items()}
    checker = AuditChecker(
        HttpAuditSource(env["clients"].user("admin.test"), step_prefix="O-auditoria"),
        subjects=subjects,
        protected_values=env["journal"].protected_values,
        wait_seconds=env["settings"].audit_wait_seconds,
        application_users={
            username: env["world"][f"usuario_{name}"] for name, username, letter, _ in OPERATIONAL_USERS if letter == "a"
        },
    )
    result = checker.check(expectations)
    problems = [
        (item.entity_type, item.missing, item.duplicates, item.wrong_actor)
        for item in result.entities
        if item.missing or item.duplicates or item.wrong_actor
    ]
    assert not problems, f"Auditoría tras la caída: {problems}"


def expected(step, service, action, entity_type, entity_id, company, actor, correlation=None):
    return ExpectedAudit(step, service, action, entity_type, str(entity_id), "COMPANY", company, actor, correlation)


def outbox_count(env, service: str, action: str, company: str, since: str, *, entity_id: str | None = None, status: str | None = None) -> int:
    settings = env["settings"]
    prefix = service.upper().replace("-", "_")
    where = [f"payload->>'action' = '{action}'", f"payload->>'company_id' = '{company}'", f"created_at >= '{since}'"]
    if entity_id:
        where.append(f"payload->>'entity_id' = '{entity_id}'")
    if status:
        where.append(f"status = '{status}'")
    rows = env["docker"].select(
        f"sio-{service}-db", settings.value(f"{prefix}_DB_USER"), settings.value(f"{prefix}_DB_NAME"),
        "SELECT count(*) FROM audit_outbox WHERE " + " AND ".join(where),
    )
    return int(rows[0][0])


# --- O1: Inventory detenido al confirmar una compra ------------------------------------------------
@pytest.mark.items(22)
@pytest.mark.evidence("O1", "outages.json")
def test_o1_inventory_down_on_purchase_confirmation(case_env, timer):
    env, world, clients, docker, journal = case_env, case_env["world"], case_env["clients"], case_env["docker"], case_env["journal"]
    ctx = world.runner.context
    compras = clients.user("compras.test")
    case = Case("O1", "sio-inventory-service")
    draft = compras.post("purchase", f"/companies/{world['empresa_a']}/purchases", step_id="O1", json_body=purchase_body(world, "O1", "2", "1000"))
    assert draft.status == 201
    purchase_id = draft.body["id"]
    before = balance_a(clients, world, "O1")
    key, correlation = ctx.idempotency_key("O1-confirmacion"), ctx.correlation_id("O1-confirmacion")
    outcome = {}

    def during():
        response = compras.post(
            "purchase", f"/companies/{world['empresa_a']}/purchases/{purchase_id}/confirmation", step_id="O1",
            json_body={"version": draft.body["version"]}, idempotency_key=key, correlation_id=correlation,
        )
        outcome["response"] = {"status": response.status, "dependency": (response.body or {}).get("dependency")}
        outcome["operation_id"] = (response.body or {}).get("operation_id")
        current = compras.get("purchase", f"/companies/{world['empresa_a']}/purchases/{purchase_id}", step_id="O1").body
        outcome["status"], outcome["pending"] = current["status"], current.get("pending_operation_id")

    with timer.measure("caidas.O1"):
        run_outage(case, docker, "sio-inventory-service",
                   lambda: ready(clients, "inventory") and http_ok(clients, "supervisor.test", "inventory", f"/companies/{world['empresa_a']}/branches/{world['sucursal_a1']}/balances", "O1-restauracion"),
                   during)
    case["response_during_outage"] = outcome["response"]
    assert outcome["response"] == {"status": 503, "dependency": "inventory"}, f"O1: respuesta durante la caída {outcome['response']}"
    assert outcome["status"] == "DRAFT" and outcome["pending"], "O1: la compra no quedó en borrador con operación pendiente"
    assert movements_for(clients, world, purchase_id, "O1") == [], "O1: hubo movimiento de inventario durante la caída"
    retry = compras.post(
        "purchase", f"/companies/{world['empresa_a']}/purchases/{purchase_id}/confirmation", step_id="O1",
        json_body={"version": draft.body["version"]}, idempotency_key=key, correlation_id=correlation,
    )
    case["after_recovery"] = {"status": retry.status, "purchase_status": (retry.body or {}).get("status")}
    assert retry.status == 200 and retry.body["status"] == "CONFIRMED", f"O1: reintento → {retry.status}"
    assert len(movements_for(clients, world, purchase_id, "O1")) == 1, "O1: la entrada se aplicó más de una vez"
    assert by_key(clients, world, outcome["operation_id"], "O1") == 200, "O1: Inventory no tiene la operación por clave"
    assert balance_a(clients, world, "O1") == before + 2
    audit_once(env, [
        expected("O1", "purchase", "CONFIRM_PURCHASE", "Purchase", purchase_id, world["empresa_a"], "compras.test"),
        expected("O1", "inventory", "APPLY_INVENTORY_ENTRY", "InventoryOperation", retry.body["inventory_operation_id"], world["empresa_a"], "compras.test"),
    ])


# --- O2: Inventory detenido al confirmar ventas; una sin reintento la cierra el conciliador -----------
@pytest.mark.items(22)
@pytest.mark.evidence("O2", "outages.json")
def test_o2_inventory_down_on_sale_confirmation_and_reconciler(case_env, timer):
    env, world, clients, docker, settings = case_env, case_env["world"], case_env["clients"], case_env["docker"], case_env["settings"]
    ctx = world.runner.context
    ventas = clients.user("ventas.test")
    case = Case("O2", "sio-inventory-service")
    sales = {}
    for name in ("reintento", "conciliador"):
        draft = ventas.post("sales", f"/companies/{world['empresa_a']}/sales", step_id="O2", json_body=sale_body(world))
        assert draft.status == 201
        sales[name] = draft.body
    before = balance_a(clients, world, "O2")
    outcome = {}

    def confirm(name):
        return ventas.post(
            "sales", f"/companies/{world['empresa_a']}/sales/{sales[name]['id']}/confirmation", step_id="O2",
            json_body={"version": sales[name]["version"]},
            idempotency_key=ctx.idempotency_key(f"O2-{name}"), correlation_id=ctx.correlation_id(f"O2-{name}"),
        )

    def during():
        for name in ("reintento", "conciliador"):
            response = confirm(name)
            outcome[name] = {"status": response.status, "dependency": (response.body or {}).get("dependency"), "operation_id": (response.body or {}).get("operation_id")}

    with timer.measure("caidas.O2"):
        run_outage(case, docker, "sio-inventory-service",
                   lambda: ready(clients, "inventory") and http_ok(clients, "supervisor.test", "inventory", f"/companies/{world['empresa_a']}/branches/{world['sucursal_a1']}/balances", "O2-restauracion"),
                   during)
        case["response_during_outage"] = outcome
        for name in ("reintento", "conciliador"):
            assert (outcome[name]["status"], outcome[name]["dependency"]) == (503, "inventory"), f"O2 {name}: {outcome[name]}"
        retry = confirm("reintento")
        assert retry.status == 200 and retry.body["status"] == "CONFIRMED", f"O2: reintento → {retry.status}"
        assert len(movements_for(clients, world, sales["reintento"]["id"], "O2")) == 1, "O2: la salida se aplicó más de una vez"
        assert by_key(clients, world, outcome["reintento"]["operation_id"], "O2") == 200
        # Segunda venta sin reintento: el conciliador real la cierra al superar su umbral (sin tocar la base).
        threshold = float(settings.value("SALES_RECONCILER_THRESHOLD_SECONDS") or 300)
        interval = float(settings.value("SALES_RECONCILER_INTERVAL_SECONDS") or 60)
        deadline = time.monotonic() + threshold + interval + RECONCILER_MARGIN_SECONDS
        operation_id = outcome["conciliador"]["operation_id"]
        status = None
        while time.monotonic() < deadline:
            response = ventas.get("sales", f"/companies/{world['empresa_a']}/sale-operations/{operation_id}", step_id="O2-conciliador")
            status = (response.body or {}).get("status")
            if status in ("FAILED", "SUCCEEDED"):
                break
            time.sleep(10)
        case["reconciler"] = {"operation_status": status, "waited_seconds": round(threshold + interval + RECONCILER_MARGIN_SECONDS - (deadline - time.monotonic()), 1)}
    assert status == "FAILED", f"O2: el conciliador no cerró la operación como FAILED (estado {status})"
    pending_sale = ventas.get("sales", f"/companies/{world['empresa_a']}/sales/{sales['conciliador']['id']}", step_id="O2-conciliador").body
    assert pending_sale["status"] == "DRAFT" and pending_sale["number"] is None, "O2: la venta conciliada no quedó en borrador"
    assert movements_for(clients, world, sales["conciliador"]["id"], "O2") == [], "O2: la venta conciliada movió inventario"
    assert balance_a(clients, world, "O2") == before - 1
    case["after_recovery"] = {"retry_status": "CONFIRMED", "reconciled_sale": pending_sale["status"]}
    audit_once(env, [
        expected("O2", "sales", "CONFIRM_SALE", "Sale", sales["reintento"]["id"], world["empresa_a"], "ventas.test"),
        expected("O2", "inventory", "APPLY_INVENTORY_OUTPUT", "InventoryOperation", retry.body["inventory_operation_id"], world["empresa_a"], "ventas.test"),
    ])


# --- O3: Commercial Relationship detenido ---------------------------------------------------------------
@pytest.mark.items(22)
@pytest.mark.evidence("O3", "outages.json")
def test_o3_commercial_relationship_down(case_env, timer):
    world, clients, docker = case_env["world"], case_env["clients"], case_env["docker"]
    ventas = clients.user("ventas.test")
    case = Case("O3", "sio-commercial-relationship-service")
    draft = ventas.post("sales", f"/companies/{world['empresa_a']}/sales", step_id="O3", json_body=sale_body(world))
    assert draft.status == 201
    count_before = ventas.get("sales", f"/companies/{world['empresa_a']}/sales", step_id="O3", params={"page_size": 1}).body["total_records"]
    before = balance_a(clients, world, "O3")
    outcome = {}

    def during():
        created = ventas.post("sales", f"/companies/{world['empresa_a']}/sales", step_id="O3", json_body=sale_body(world))
        outcome["create"] = {"status": created.status, "dependency": (created.body or {}).get("dependency")}
        confirmed = ventas.post(
            "sales", f"/companies/{world['empresa_a']}/sales/{draft.body['id']}/confirmation", step_id="O3",
            json_body={"version": draft.body["version"]}, idempotency_key=world.runner.context.idempotency_key("O3-confirmacion"),
        )
        outcome["confirm"] = {"status": confirmed.status, "dependency": (confirmed.body or {}).get("dependency")}

    with timer.measure("caidas.O3"):
        run_outage(case, docker, "sio-commercial-relationship-service",
                   lambda: ready(clients, "commercial-relationship") and http_ok(clients, "admin.test", "commercial-relationship", f"/company-products/{world['producto_empresa_a']}", "O3-restauracion"),
                   during)
    case["response_during_outage"] = outcome
    assert outcome["create"] == {"status": 503, "dependency": "commercial-relationship"}, f"O3 alta: {outcome['create']}"
    assert outcome["confirm"]["status"] == 503, f"O3 confirmación: {outcome['confirm']}"
    count_after = ventas.get("sales", f"/companies/{world['empresa_a']}/sales", step_id="O3", params={"page_size": 1}).body["total_records"]
    assert count_after == count_before, "O3: se creó una venta durante la caída"
    current = ventas.get("sales", f"/companies/{world['empresa_a']}/sales/{draft.body['id']}", step_id="O3").body
    assert current["status"] == "DRAFT" and current["number"] is None, "O3: el borrador cambió durante la caída"
    assert balance_a(clients, world, "O3") == before, "O3: hubo movimiento de inventario"
    case["after_recovery"] = {"draft_status": current["status"]}


def new_person(world, journal, label: str) -> str:
    from sio_mvp.identities import conforming_number

    admin = world.runner.clients.user("admin.test")
    for attempt in range(1, 6):
        number = conforming_number(world["patron_cc"], world.runner.context, label, attempt)
        journal.protect(number)
        response = admin.post("party-identity", "/person-identities", step_id=label, json_body={
            "identification_country_id": world["pais_co"], "identification_type": "CC", "identification_number": number,
            "first_name": f"{label.upper().replace('-', '')}{world['run']}", "last_name": "DATO FICTICIO DE VALIDACION", "birth_date": "1990-01-01",
        })
        if response.status == 201:
            return response.body["id"]
        assert response.status == 409
    raise AssertionError(f"{label}: sin cédula libre")


# --- O4a: solo Party Identity detenido ------------------------------------------------------------------
@pytest.mark.items(22)
@pytest.mark.evidence("O4a", "outages.json")
def test_o4a_party_identity_down_on_customer(case_env, timer):
    env, world, clients, docker, journal = case_env, case_env["world"], case_env["clients"], case_env["docker"], case_env["journal"]
    admin = clients.user("admin.test")
    case = Case("O4a", "sio-party-identity-service")
    person = new_person(world, journal, "O4a-persona")
    body = {"customer_kind": "PERSON", "person_identity_id": person, "internal_code": f"O4A-{world['run']}", "display_name": f"Cliente O4a {world['run']} (dato ficticio)"}
    path = f"/companies/{world['empresa_a']}/company-customers"
    count_before = admin.get("commercial-relationship", path, step_id="O4a", params={"page_size": 1, "status": "ALL"}).body["total_records"]
    since = now_iso()
    outcome = {}

    def during():
        assert docker.inspect("sio-operational-context-service").healthy, "O4a: Operational Context debe seguir en pie"
        response = admin.post("commercial-relationship", path, step_id="O4a", json_body=body)
        outcome["create"] = {"status": response.status, "dependency": (response.body or {}).get("dependency")}

    with timer.measure("caidas.O4a"):
        run_outage(case, docker, "sio-party-identity-service",
                   lambda: ready(clients, "party-identity") and http_ok(clients, "admin.test", "party-identity", f"/person-identities/{person}", "O4a-restauracion"),
                   during)
    case["response_during_outage"] = outcome
    assert outcome["create"] == {"status": 503, "dependency": "party-identity"}, f"O4a: {outcome['create']}"
    count_after = admin.get("commercial-relationship", path, step_id="O4a", params={"page_size": 1, "status": "ALL"}).body["total_records"]
    assert count_after == count_before, "O4a: se creó un cliente durante la caída"
    assert outbox_count(env, "commercial-relationship", "CREATE_COMPANY_CUSTOMER", world["empresa_a"], since) == 0, "O4a: evento en la outbox de CR"
    created = admin.post("commercial-relationship", path, step_id="O4a", json_body=body)
    assert created.status == 201, f"O4a: el alta tras restaurar → {created.status}"
    count_final = admin.get("commercial-relationship", path, step_id="O4a", params={"page_size": 1, "status": "ALL"}).body["total_records"]
    assert count_final == count_before + 1, "O4a: el alta no quedó una sola vez"
    case["after_recovery"] = {"status": created.status}
    audit_once(env, [expected("O4a", "commercial-relationship", "CREATE_COMPANY_CUSTOMER", "CompanyCustomer", created.body["id"], world["empresa_a"], "admin.test")])


# --- O4b: solo Operational Context detenido (después de O4a restaurado) ---------------------------------
@pytest.mark.items(22)
@pytest.mark.evidence("O4b", "outages.json")
def test_o4b_operational_context_down_on_purchase_draft(case_env, timer):
    env, world, clients, docker = case_env, case_env["world"], case_env["clients"], case_env["docker"]
    assert STATE["outages"] and STATE["outages"][-1]["case"] == "O4a" and STATE["outages"][-1]["restored"], "O4b solo después de restaurar O4a"
    compras = clients.user("compras.test")
    case = Case("O4b", "sio-operational-context-service")
    path = f"/companies/{world['empresa_a']}/purchases"
    body = purchase_body(world, "O4b", "1", "1000")
    count_before = clients.user("admin.test").get("purchase", path, step_id="O4b", params={"page_size": 1}).body["total_records"]
    since = now_iso()
    outcome = {}

    def during():
        assert docker.inspect("sio-party-identity-service").healthy, "O4b: Party Identity debe seguir en pie"
        response = compras.post("purchase", path, step_id="O4b", json_body=body)
        outcome["create"] = {"status": response.status, "dependency": (response.body or {}).get("dependency")}

    with timer.measure("caidas.O4b"):
        run_outage(case, docker, "sio-operational-context-service",
                   lambda: ready(clients, "operational-context") and http_ok(clients, "admin.test", "operational-context", f"/companies/{world['empresa_a']}", "O4b-restauracion"),
                   during)
    case["response_during_outage"] = outcome
    assert outcome["create"] == {"status": 503, "dependency": "operational-context"}, f"O4b: {outcome['create']}"
    count_after = clients.user("admin.test").get("purchase", path, step_id="O4b", params={"page_size": 1}).body["total_records"]
    assert count_after == count_before, "O4b: se creó una compra durante la caída"
    assert outbox_count(env, "purchase", "CREATE_PURCHASE", world["empresa_a"], since) == 0, "O4b: evento en la outbox de Purchase"
    created = compras.post("purchase", path, step_id="O4b", json_body=body)
    assert created.status == 201, f"O4b: el borrador tras restaurar → {created.status}"
    count_final = clients.user("admin.test").get("purchase", path, step_id="O4b", params={"page_size": 1}).body["total_records"]
    assert count_final == count_before + 1, "O4b: el borrador no quedó una sola vez"
    case["after_recovery"] = {"status": created.status}
    audit_once(env, [expected("O4b", "purchase", "CREATE_PURCHASE", "Purchase", created.body["id"], world["empresa_a"], "compras.test")])


# --- O5: Audit detenido ----------------------------------------------------------------------------------
@pytest.mark.items(22)
@pytest.mark.evidence("O5", "outages.json")
def test_o5_audit_down_events_delivered_once(case_env, timer):
    env, world, clients, docker = case_env, case_env["world"], case_env["clients"], case_env["docker"]
    ctx = world.runner.context
    compras, ventas = clients.user("compras.test"), clients.user("ventas.test")
    case = Case("O5", "sio-audit-service")
    purchase = compras.post("purchase", f"/companies/{world['empresa_a']}/purchases", step_id="O5", json_body=purchase_body(world, "O5", "1", "1000")).body
    sale = ventas.post("sales", f"/companies/{world['empresa_a']}/sales", step_id="O5", json_body=sale_body(world)).body
    outcome = {}

    def during():
        confirmed_purchase = compras.post(
            "purchase", f"/companies/{world['empresa_a']}/purchases/{purchase['id']}/confirmation", step_id="O5",
            json_body={"version": purchase["version"]}, idempotency_key=ctx.idempotency_key("O5-compra"), correlation_id=ctx.correlation_id("O5-compra"),
        )
        confirmed_sale = ventas.post(
            "sales", f"/companies/{world['empresa_a']}/sales/{sale['id']}/confirmation", step_id="O5",
            json_body={"version": sale["version"]}, idempotency_key=ctx.idempotency_key("O5-venta"), correlation_id=ctx.correlation_id("O5-venta"),
        )
        outcome["purchase"] = confirmed_purchase.status
        outcome["sale"] = confirmed_sale.status
        outcome["purchase_operation"] = (confirmed_purchase.body or {}).get("inventory_operation_id")
        outcome["sale_operation"] = (confirmed_sale.body or {}).get("inventory_operation_id")
        outcome["pending"] = {
            "purchase": outbox_count(env, "purchase", "CONFIRM_PURCHASE", world["empresa_a"], "1970-01-01", entity_id=purchase["id"], status="PENDING"),
            "sales": outbox_count(env, "sales", "CONFIRM_SALE", world["empresa_a"], "1970-01-01", entity_id=sale["id"], status="PENDING"),
            "inventory": outbox_count(env, "inventory", "APPLY_INVENTORY_ENTRY", world["empresa_a"], "1970-01-01", entity_id=outcome["purchase_operation"] or "-", status="PENDING"),
        }

    with timer.measure("caidas.O5"):
        run_outage(case, docker, "sio-audit-service",
                   lambda: ready(clients, "audit") and http_ok(clients, "admin.test", "audit", f"/companies/{world['empresa_a']}/audit-events", "O5-restauracion"),
                   during)
    case["response_during_outage"] = {key: outcome[key] for key in ("purchase", "sale", "pending")}
    assert (outcome["purchase"], outcome["sale"]) == (200, 200), f"O5: confirmaciones durante la caída {outcome}"
    assert all(count == 1 for count in outcome["pending"].values()), f"O5: eventos PENDING en las outbox {outcome['pending']}"
    with timer.measure("caidas.O5.entrega"):
        audit_once(env, [
            expected("O5", "purchase", "CONFIRM_PURCHASE", "Purchase", purchase["id"], world["empresa_a"], "compras.test"),
            expected("O5", "sales", "CONFIRM_SALE", "Sale", sale["id"], world["empresa_a"], "ventas.test"),
            expected("O5", "inventory", "APPLY_INVENTORY_ENTRY", "InventoryOperation", outcome["purchase_operation"], world["empresa_a"], "compras.test"),
            expected("O5", "inventory", "APPLY_INVENTORY_OUTPUT", "InventoryOperation", outcome["sale_operation"], world["empresa_a"], "ventas.test"),
        ])
    case["after_recovery"] = {"delivered_once": True}


# --- O6: base de datos de Sales detenida -------------------------------------------------------------------
@pytest.mark.items(22)
@pytest.mark.evidence("O6", "outages.json")
def test_o6_sales_database_down_recovers_without_restart(case_env, timer):
    world, clients, docker = case_env["world"], case_env["clients"], case_env["docker"]
    ventas = clients.user("ventas.test")
    case = Case("O6", "sio-sales-db")
    started_before = docker.inspect("sio-sales-service").started_at
    path = f"/companies/{world['empresa_a']}/sales"
    outcome = {}

    def during():
        read = ventas.get("sales", path, step_id="O6", params={"page_size": 1})
        created = ventas.post("sales", path, step_id="O6", json_body=sale_body(world))
        outcome["read"] = read.status
        outcome["create"] = created.status

    with timer.measure("caidas.O6"):
        run_outage(case, docker, "sio-sales-db", lambda: docker.inspect("sio-sales-db").healthy, during)
    case["response_during_outage"] = outcome
    assert outcome == {"read": 503, "create": 503}, f"O6: respuestas durante la caída {outcome}"
    deadline = time.monotonic() + 60
    status = None
    while time.monotonic() < deadline:
        status = ventas.get("sales", path, step_id="O6", params={"page_size": 1}).status
        if status == 200:
            break
        time.sleep(2)
    assert status == 200, f"O6: Sales no se recuperó sin reinicio (último estado {status})"
    started_after = docker.inspect("sio-sales-service").started_at
    case["after_recovery"] = {"status": status, "sales_service_restarted": started_after != started_before}
    assert started_after == started_before, "O6: el contenedor de Sales se reinició"


@pytest.mark.items(22)
@pytest.mark.evidence("outages.json")
def test_environment_as_at_start(docker, report_dir):
    """Todos los contenedores gestionados que estaban sanos al inicio de la corrida siguen sanos (T053)."""
    path = report_dir / "containers-start.json"
    if not path.is_file():
        pytest.skip("Sin estado inicial de la corrida (etapa ejecutada fuera de run.py)")
    start = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    for name, state in start.items():
        was_healthy = state["status"] == "running" and state["health"] in (None, "healthy")
        if was_healthy and not docker.inspect(name).healthy:
            problems.append(name)
    assert not problems, f"Contenedores que no quedaron como al inicio: {problems}"
