"""Historia 3: acceso operativo del usuario en Sales e Inventory (spec 025, T014).

Cada caso se observa en dos consumidores. Lo grabado con las lecturas por HTTP debe repetirse igual con las
lecturas por contrato; además, con ``contract`` no debe haber ninguna solicitud a ``/operational-access``.

Mundo propio de la prueba (empresas ficticias nuevas en cada ejecución):

| Empresa | Estado | Miembros | Sucursales |
|---|---|---|---|
| C | activa | admin (activo), supervisor (activo) | B1 (admin y supervisor, la de supervisor inactiva), B2 (nadie), B3 (inactiva, admin), B4 (admin; se inactiva en el caso de bloqueo inmediato) |
| D | inactiva | admin | D1 (admin) |
| E | activa | supervisor (membresía inactiva), admin | E1 (supervisor) |

PERMISSION_DENIED no se puede provocar aquí: todos los grupos de prueba tienen
``perm:operational-context:application_users:read``. Lo cubren las pruebas de paridad (T019) y de adaptador (T025).
"""

from __future__ import annotations

import time
from uuid import uuid4

import pytest
from conftest import URLS, expect, outages_only
from support import Normalizer, RequestWindow, matching, outage_case, owner_database_down, response_case

OC, SALES, INV = URLS["operational_context"], URLS["sales"], URLS["inventory"]
CONTAINERS = ("sio-it-operational-context-service", "sio-it-sales-service", "sio-it-inventory-service")
ACCESS = ("operational-context GET /api/v1/operational-access",)


@pytest.fixture(scope="module")
def world(seed, users, run_id):
    admin = users("admin.test")
    colombia = expect(admin.get(f"{URLS['geography']}/global-countries", params={"iso3_code": "COL"}))["items"][0]["id"]

    def branch(company_id: str, code: str) -> dict:
        return expect(admin.post(f"{OC}/companies/{company_id}/branches", json={
            "code": f"{code}{run_id}", "name": f"Sucursal ficticia {code} {run_id}"}))

    def assign(member_id: str, branch_id: str) -> dict:
        return expect(admin.post(f"{OC}/application-users/{member_id}/user-branches", json={"branch_id": branch_id}))

    def deactivate(path: str, entity: dict) -> dict:
        return expect(admin.post(f"{OC}/{path}/{entity['id']}/deactivate", json={"version": entity["version"]}))

    c = seed.company(admin, colombia, f"US3C{run_id}")
    d = seed.company(admin, colombia, f"US3D{run_id}")
    e = seed.company(admin, colombia, f"US3E{run_id}")
    admin_c = seed.member(admin, colombia, c, "admin.test")
    supervisor_c = seed.member(admin, colombia, c, "supervisor.test")
    admin_d = seed.member(admin, colombia, d, "admin.test")
    seed.member(admin, colombia, e, "admin.test")
    supervisor_e = seed.member(admin, colombia, e, "supervisor.test")

    b1, b2, b3, b4 = (branch(c, code) for code in ("B1", "B2", "B3", "B4"))
    d1, e1 = branch(d, "D1"), branch(e, "E1")
    for target in (b1, b3, b4):
        assign(admin_c, target["id"])
    deactivate("user-branches", assign(supervisor_c, b1["id"]))
    assign(admin_d, d1["id"])
    assign(supervisor_e, e1["id"])

    deactivate("branches", b3)
    company_d = expect(admin.get(f"{OC}/companies/{d}"))
    deactivate("companies", company_d)
    member_e = expect(admin.get(f"{OC}/application-users/{supervisor_e}"))
    deactivate("application-users", member_e)

    aliases = {c: "empresa_C", d: "empresa_D", e: "empresa_E", b1["id"]: "B1", b2["id"]: "B2", b3["id"]: "B3",
               b4["id"]: "B4", d1["id"]: "D1", e1["id"]: "E1", admin_c: "admin_C", supervisor_c: "supervisor_C",
               admin_d: "admin_D", supervisor_e: "supervisor_E"}
    return {"C": c, "D": d, "E": e, "B1": b1["id"], "B2": b2["id"], "B3": b3["id"], "B4": b4, "D1": d1["id"],
            "E1": e1["id"], "admin_C": admin_c, "aliases": aliases, "run": run_id, "deactivate": deactivate}


def sales_company(client, company_id):
    return client.get(f"{SALES}/companies/{company_id}/sales", params={"page_size": 1})


def sales_branch(client, company_id, branch_id):
    # Pasa la verificación de acceso antes que cualquier otra; si se permite, falla después por el cliente inexistente.
    return client.post(
        f"{SALES}/companies/{company_id}/sales",
        headers={"Idempotency-Key": str(uuid4())},
        json={"branch_id": branch_id, "company_customer_id": str(uuid4()), "payment_method_id": str(uuid4()), "lines": []},
    )


def inventory_company(client, company_id):
    return client.get(f"{INV}/companies/{company_id}/inventory-adjustments")


def inventory_branch(client, company_id, branch_id):
    # Si se permite, falla después porque el producto de la empresa no existe.
    return client.post(f"{INV}/companies/{company_id}/inventory-adjustments", json={
        "adjustment_key": str(uuid4()), "branch_id": branch_id, "company_product_id": str(uuid4()),
        "adjustment_type": "NEGATIVE", "quantity": "1", "reason": "Caracterización spec 025"})


CONSUMERS = {
    "sales": (sales_company, sales_branch),
    "inventory": (inventory_company, inventory_branch),
}

# (nombre, usuario, empresa, sucursal o None, causa en Operational Context)
MATRIX = [
    ("permitido_empresa", "admin.test", "C", None, "allowed"),
    ("permitido_sucursal", "admin.test", "C", "B1", "allowed"),
    ("no_miembro_empresa_inexistente", "admin.test", "NUEVA", None, "USER_NOT_MEMBER"),
    ("no_miembro_sucursal_inexistente", "admin.test", "C", "NUEVA", "USER_NOT_MEMBER"),
    ("no_miembro_empresa_ajena", "supervisor.test", "D", None, "USER_NOT_MEMBER"),
    ("no_miembro_sucursal_ajena", "supervisor.test", "D", "D1", "USER_NOT_MEMBER"),
    ("membresia_inactiva_empresa", "supervisor.test", "E", None, "USER_MEMBERSHIP_INACTIVE"),
    ("membresia_inactiva_sucursal", "supervisor.test", "E", "E1", "USER_MEMBERSHIP_INACTIVE"),
    ("empresa_inactiva_lectura", "admin.test", "D", None, "COMPANY_INACTIVE"),
    ("empresa_inactiva_sucursal", "admin.test", "D", "D1", "COMPANY_INACTIVE"),
    ("sucursal_inactiva", "admin.test", "C", "B3", "BRANCH_INACTIVE"),
    ("sucursal_no_asignada", "admin.test", "C", "B2", "BRANCH_NOT_ASSIGNED"),
    ("asignacion_inactiva", "supervisor.test", "C", "B1", "USER_BRANCH_INACTIVE"),
]


def _resolve(world, key):
    if key is None:
        return None
    if key == "NUEVA":
        return str(uuid4())
    value = world[key]
    return value["id"] if isinstance(value, dict) else value


def _observe(world, users, consumer, username, company_key, branch_key):
    company_check, branch_check = CONSUMERS[consumer]
    client = users(username)
    company_id = _resolve(world, company_key)
    branch_id = _resolve(world, branch_key)
    normalizer = Normalizer(world["aliases"], run=world["run"])
    window = RequestWindow(CONTAINERS)
    response = company_check(client, company_id) if branch_id is None else branch_check(client, company_id, branch_id)
    window.close()
    return response_case(response, normalizer), window.counts()


@pytest.mark.parametrize("consumer", sorted(CONSUMERS))
@pytest.mark.parametrize(("name", "username", "company", "branch", "cause"), MATRIX, ids=[row[0] for row in MATRIX])
def test_access_matrix(world, users, book, reads, consumer, name, username, company, branch, cause):
    case, requests = _observe(world, users, consumer, username, company, branch)
    case["causa_oc"] = cause
    book.check(f"{consumer}:{name}", case, requests=requests)
    calls = matching(requests, ACCESS)
    if reads == "contract":
        assert calls == 0, f"{consumer}:{name} llamó a /operational-access con lecturas por contrato: {requests}"
    else:
        assert calls >= 1, f"{consumer}:{name}: con http se esperaba la verificación por HTTP: {requests}"


@pytest.mark.parametrize("consumer", sorted(CONSUMERS))
def test_branch_deactivation_blocks_immediately(world, users, book, consumer, run_id, seed):
    """Se permite en B4; se inactiva B4; la petición siguiente ya se rechaza (sin caché, FR-034)."""
    admin = users("admin.test")
    target = expect(admin.post(f"{OC}/companies/{world['C']}/branches", json={
        "code": f"B4{consumer[:3].upper()}{run_id}", "name": f"Sucursal ficticia bloqueo {consumer} {run_id}"}))
    expect(admin.post(f"{OC}/application-users/{world['admin_C']}/user-branches", json={"branch_id": target["id"]}))
    aliases = {**world["aliases"], target["id"]: "B4"}
    _, branch_check = CONSUMERS[consumer]

    before = response_case(branch_check(admin, world["C"], target["id"]), Normalizer(aliases, run=run_id))
    world["deactivate"]("branches", target)
    after = response_case(branch_check(admin, world["C"], target["id"]), Normalizer(aliases, run=run_id))

    book.check(f"{consumer}:bloqueo_inmediato", {"antes": before, "despues": after})
    assert before["status"] not in (403, 404)
    assert after["status"] == 403


@outages_only
def test_caida_de_operational_context(world, users, outage_book):
    """T079: con la base de Operational Context caída, cada consumidor que verifica el acceso del usuario responde el
    503 de hoy, a tiempo: Sales, Inventory, Commercial Relationship y Audit (los demás, en sus historias)."""
    admin = users("admin.test")
    company = world["C"]
    checks = {
        "sales": lambda: sales_company(admin, company),
        "inventory": lambda: inventory_company(admin, company),
        "commercial-relationship": lambda: admin.get(f"{URLS['commercial_relationship']}/companies/{company}/company-products",
                                                     params={"page_size": 1}),
        "audit": lambda: admin.get(f"{URLS['audit']}/companies/{company}/audit-events", params={"page_size": 1}),
    }
    observed = {}
    with owner_database_down("operational-context"):
        for consumer, action in checks.items():
            start = time.monotonic()
            response = action()
            observed[consumer] = (response, time.monotonic() - start)
    normalizer = Normalizer(world["aliases"], run=world["run"])
    for consumer, (response, elapsed) in observed.items():
        outage_book.check(f"operational-context:{consumer}", outage_case(response, normalizer, elapsed, 5.5, {}))
