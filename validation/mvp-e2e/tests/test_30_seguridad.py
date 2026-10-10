"""Etapa `seguridad`: aislamiento entre empresas y permisos (Historia 4; ítem 21; FR-015, FR-016).

Usa el mundo de la corrida (empresas A y B, compras y ventas del recorrido). El rechazo por aislamiento
se exige con un usuario que tiene el permiso y no la membresía (R-11); el cuerpo no puede contener ids ni
datos de la empresa ajena (RC-04). Ningún caso cambia datos: se comprueba antes y después.
"""

from __future__ import annotations

import pytest

from scenario import security
from scenario.steps import resolve

pytestmark = pytest.mark.e2e

A_DATA = (
    "empresa_a", "sucursal_a1", "org_empresa_a", "compra_1", "venta_2", "cliente", "proveedor",
    "producto_empresa_a", "producto_empresa_b", "lista_general", "lista_mayorista", "item_general",
    "usuario_admin", "usuario_compras", "usuario_ventas",
)
B_DATA = ("empresa_b", "sucursal_b1", "org_empresa_b", "usuario_reportes", "usuario_inventario")


def without_instance(body):
    """`instance` repite la ruta pedida por el propio cliente; no es un dato revelado."""
    if isinstance(body, dict):
        return {key: value for key, value in body.items() if key != "instance"}
    return body


def leaked(world, journal, body, names) -> list[str]:
    text = journal.safe_text(without_instance(body))
    return [name for name in names if world.vars.get(name) and str(world.vars[name]) in text]


def counts(world, clients, step_id: str) -> dict:
    admin = clients.user("admin.test")
    company = world["empresa_a"]
    result = {}
    for service, path in (("purchase", f"/companies/{company}/purchases"), ("sales", f"/companies/{company}/sales")):
        response = admin.get(service, path, step_id=step_id, params={"page_size": 1})
        assert response.status == 200
        result[service] = response.body["total_records"]
    balance = admin.get("inventory", f"/companies/{company}/branches/{world['sucursal_a1']}/balances/{world['producto_empresa_a']}", step_id=step_id)
    result["saldo_a"] = balance.body["quantity"]
    return result


@pytest.fixture(scope="module")
def before(world, clients):
    if "compra_1" not in world.vars or "venta_2" not in world.vars:
        pytest.skip("BLOQUEADO: la etapa seguridad necesita las compras y ventas del recorrido de esta corrida")
    world.vars.setdefault("clave_ajuste", world.runner.context.correlation_id("I-05.ajuste"))
    return counts(world, clients, "seguridad-antes")


@pytest.mark.items(21)
@pytest.mark.evidence("§3")
@pytest.mark.parametrize("step", security.ISOLATION, ids=lambda step: step.id)
def test_isolation_between_companies(world, journal, before, step):
    response = world.runner.run(step)
    foreign = B_DATA if step.path.startswith("/companies/{empresa_b}") else A_DATA
    found = leaked(world, journal, response.body, foreign)
    assert not found, f"{step.id}: el cuerpo revela datos de la empresa ajena: {found}"


@pytest.mark.items(21)
@pytest.mark.evidence("§4")
@pytest.mark.parametrize("step", security.PERMISSIONS, ids=lambda step: step.id)
def test_permission_matrix(world, before, step):
    world.runner.run(step)


@pytest.mark.items(21)
@pytest.mark.evidence("S-06")
@pytest.mark.parametrize("step", security.UNAUTHENTICATED, ids=lambda step: step.id)
def test_without_token_or_with_invalid_token(world, before, step):
    world.runner.run(step)


@pytest.mark.items(21)
@pytest.mark.evidence("S-07", "V-06")
def test_s07_cost_and_margin_only_with_profitability(world, journal):
    seller = world.run("V-06.vendedor").body
    supervisor = world.run("V-06.supervisor").body
    for field in ("unit_cost_snapshot", "cost_total", "cost_known", "gross_margin_amount", "gross_margin_percentage"):
        assert field not in seller["lines"][0], f"S-07: ventas.test recibe {field}"
        assert field in supervisor["lines"][0], f"S-07: supervisor.test no recibe {field}"


@pytest.mark.items(21)
@pytest.mark.evidence("§3", "§4")
def test_no_data_changed(world, clients, journal, before):
    after = counts(world, clients, "seguridad-despues")
    ok = journal.verify("seguridad", "sin cambios en compras, ventas y saldo", expected=before, obtained=after)
    assert ok, f"La etapa seguridad cambió datos: antes {before}, después {after}"
