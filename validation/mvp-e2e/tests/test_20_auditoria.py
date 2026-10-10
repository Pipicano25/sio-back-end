"""Etapa `recorrido` (final): auditoría del recorrido (Historia 2; U-01, U-02; ítem 19).

Se ejecuta en el mismo proceso que `test_10_recorrido.py`: la auditoría esperada la declaró cada paso
al ejecutarse (acciones de `specs/016-existing-services-audit/contracts/audit-actions.md` y de las Specs
012–015). Si un nombre o un actor observado difiere del contrato, es una brecha, no un ajuste.
"""

from __future__ import annotations

import json

import pytest

from sio_mvp.journal import ExpectedAudit
from sio_mvp.audit_check import Absence, AuditChecker, HttpAuditSource

pytestmark = pytest.mark.e2e
STATE: dict = {}
SERVICE_ACCOUNTS = (
    "commercial-relationship-service",
    "purchase-service",
    "sales-service",
    "inventory-service",
    "product-catalog-service",
    "party-identity-service",
    "operational-context-service",
)


def subjects(realm) -> dict[str, str]:
    mapping = {username: user["id"] for username, user in realm.users.items()}
    for client in SERVICE_ACCOUNTS:
        name = f"service-account-{client}"
        if name in realm.users:
            mapping[name] = realm.users[name]["id"]
    return mapping


def application_users(world) -> dict[str, str]:
    """Usuario de prueba → usuario operativo en la empresa A (actor de Purchase y Sales)."""
    from scenario.steps import OPERATIONAL_USERS

    return {username: world[f"usuario_{name}"] for name, username, letter, _ in OPERATIONAL_USERS if letter == "a"}


def load_expected(journal, report_dir) -> list[ExpectedAudit]:
    if journal.expected_audits:
        return list(journal.expected_audits)
    path = report_dir / "audit-expected.json"
    if path.is_file():  # repetición de la verificación sobre la misma corrida
        return [ExpectedAudit(**item) for item in json.loads(path.read_text(encoding="utf-8"))]
    return []


@pytest.fixture(scope="module")
def audit_result(world, clients, journal, settings, realm, report_dir, timer):
    company = world["empresa_a"]
    every = load_expected(journal, report_dir)
    if not every:
        pytest.skip("BLOQUEADO: no hay auditoría esperada (el recorrido no se ejecutó en esta etapa)")
    # U-01 (contracts/e2e-scenarios.md §2): historial de la empresa A y de plataforma. Las entidades de la
    # empresa B (ajena) no las lee ningún usuario de prueba con lectura de auditoría y membresía en B.
    expected = [item for item in every if item.scope == "PLATFORM" or item.company_id == company]
    journal.record({"step_id": "U-01", "expected_total": len(every), "expected_company_a_and_platform": len(expected)})
    absences = [
        Absence("COMPANY", company, "Sale", world[f"venta_{number}"], "CONFIRM_SALE") for number in ("4", "5", "7")
    ]
    checker = AuditChecker(
        HttpAuditSource(clients.user("admin.test")),
        subjects=subjects(realm),
        protected_values=journal.protected_values,
        wait_seconds=settings.audit_wait_seconds,
        application_users=application_users(world),
    )
    with timer.measure("recorrido.auditoria"):
        result = checker.check(expected, absences=absences)
    if journal.expected_audits:
        journal.write_expected_audit()
    result.write(report_dir)
    STATE["result"] = result
    return result


@pytest.mark.items(19)
@pytest.mark.evidence("U-01", "audit-check.json")
def test_u01_each_expected_action_exactly_once(audit_result, journal):
    failing = [
        {
            "entity": f"{item.entity_type}/{item.entity_id}",
            "steps": item.steps,
            "missing": item.missing,
            "duplicates": item.duplicates,
            "wrong_actor": item.wrong_actor,
            "wrong_scope": item.wrong_scope,
            "wrong_result": item.wrong_result,
            "out_of_order": item.out_of_order,
            "unexpected_present": item.unexpected_present,
            "correlation_missing": item.correlation_missing,
        }
        for item in audit_result.entities
        if item.missing or item.duplicates or item.wrong_actor or item.wrong_scope or item.wrong_result or item.out_of_order or item.unexpected_present or item.correlation_missing
    ]
    journal.record({"step_id": "U-01", "summary": audit_result.summary, "waited_seconds": round(audit_result.waited_seconds, 1)})
    assert not failing, "U-01: auditoría distinta de la esperada: " + journal.safe_text(failing)


@pytest.mark.items(19)
@pytest.mark.evidence("U-02", "audit-check.json")
def test_u02_no_protected_values_nor_cost_in_events(audit_result, journal):
    protected = [item.protected for item in audit_result.entities if item.protected]
    cost = [item.cost_fields for item in audit_result.entities if item.cost_fields]
    assert not protected, "U-02: valores protegidos en eventos de Audit: " + journal.safe_text(protected)
    assert not cost, "U-02: campos de costo o margen en eventos de Sales: " + journal.safe_text(cost)


@pytest.mark.items(19)
@pytest.mark.evidence("U-02.vendedor")
def test_u02_seller_cannot_read_audit(world):
    world.run("U-02.vendedor")
