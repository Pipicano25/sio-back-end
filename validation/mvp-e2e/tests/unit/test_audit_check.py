"""T037 — Verificación de la auditoría del recorrido (sio_mvp.audit_check) con historiales simulados."""

import pytest

from sio_mvp.audit_check import AuditChecker, Absence
from sio_mvp.journal import ExpectedAudit

pytestmark = pytest.mark.unit

SUBS = {"admin.test": "sub-admin", "compras.test": "sub-compras", "service-account-commercial-relationship-service": "sub-cr"}
COMPANY = "c-1"


def expected(action, entity_id="e-1", *, entity_type="Purchase", scope="COMPANY", actor="compras.test", correlation=None, step="P-01", result="SUCCESS"):
    return ExpectedAudit(step, "purchase", action, entity_type, entity_id, scope, COMPANY if scope == "COMPANY" else None, actor, correlation, result)


def event(action, entity_id="e-1", *, at="2026-10-09T10:00:00Z", sub="sub-compras", company=COMPANY, new=None, previous=None, correlation=None, source="purchase-service", entity_type="Purchase"):
    return {
        "id": f"{action}-{entity_id}-{at}",
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "company_id": company,
        "keycloak_user_id": sub,
        "occurred_at": at,
        "new_values": new,
        "previous_values": previous,
        "correlation_id": correlation,
        "source_service": source,
        "result": "SUCCESS",
    }


class FakeAudit:
    def __init__(self, history, by_correlation=None, rounds_until_complete=0):
        self.history = history
        self.by_correlation = by_correlation or {}
        self.rounds = rounds_until_complete
        self.calls = 0

    def entity_history(self, scope, company_id, entity_type, entity_id):
        self.calls += 1
        events = self.history.get((entity_type, entity_id), [])
        if self.rounds > 0:
            self.rounds -= 1
            return events[:-1]
        return events

    def by_correlation_id(self, company_id, correlation_id):
        return self.by_correlation.get(correlation_id, [])


def checker(fake, **kwargs):
    clock = {"now": 0.0}
    kwargs.setdefault("protected_values", set())
    return AuditChecker(
        fake,
        subjects=SUBS,
        wait_seconds=kwargs.pop("wait_seconds", 10),
        sleep=lambda seconds: clock.__setitem__("now", clock["now"] + seconds),
        clock=lambda: clock["now"],
        **kwargs,
    )


def test_ok_when_each_action_appears_once_in_order():
    fake = FakeAudit(
        {
            ("Purchase", "e-1"): [
                event("CREATE_PURCHASE", at="2026-10-09T10:00:00Z"),
                event("CONFIRM_PURCHASE", at="2026-10-09T10:01:00Z"),
            ]
        }
    )
    result = checker(fake).check([expected("CREATE_PURCHASE"), expected("CONFIRM_PURCHASE")])
    assert result.ok
    assert result.summary == {"expected": 2, "received": 2, "missing": 0, "duplicates": 0, "wrong_actor": 0, "wrong_scope": 0, "wrong_result": 0, "out_of_order": 0, "protected": 0, "cost_fields": 0, "unexpected_present": 0, "correlation_missing": 0}


def test_detects_missing_and_duplicates():
    fake = FakeAudit({("Purchase", "e-1"): [event("CREATE_PURCHASE"), event("CREATE_PURCHASE", at="2026-10-09T10:00:01Z")]})
    result = checker(fake, wait_seconds=4).check([expected("CREATE_PURCHASE"), expected("CONFIRM_PURCHASE")])
    assert not result.ok
    assert result.summary["missing"] == 1
    assert result.summary["duplicates"] == 1


def test_waits_for_delivery_within_the_limit():
    fake = FakeAudit({("Purchase", "e-1"): [event("CREATE_PURCHASE")]}, rounds_until_complete=2)
    result = checker(fake, wait_seconds=30).check([expected("CREATE_PURCHASE")])
    assert result.ok
    assert fake.calls >= 3


def test_wait_is_bounded():
    fake = FakeAudit({})
    result = checker(fake, wait_seconds=6).check([expected("CREATE_PURCHASE")])
    assert not result.ok
    assert result.waited_seconds <= 8


def test_detects_wrong_actor_and_scope():
    fake = FakeAudit(
        {
            ("Purchase", "e-1"): [event("CREATE_PURCHASE", sub="sub-admin")],
            ("Product", "p-1"): [event("REGISTER_PRODUCT_FIRST_USE", "p-1", sub="sub-cr", company="c-1", entity_type="Product")],
        }
    )
    result = checker(fake).check(
        [
            expected("CREATE_PURCHASE"),
            expected("REGISTER_PRODUCT_FIRST_USE", "p-1", entity_type="Product", scope="PLATFORM", actor="service-account-commercial-relationship-service"),
        ]
    )
    assert result.summary["wrong_actor"] == 1
    assert result.summary["wrong_scope"] == 1


def test_detects_out_of_order():
    fake = FakeAudit(
        {
            ("Purchase", "e-1"): [
                event("CONFIRM_PURCHASE", at="2026-10-09T10:00:00Z"),
                event("CREATE_PURCHASE", at="2026-10-09T10:01:00Z"),
            ]
        }
    )
    result = checker(fake).check([expected("CREATE_PURCHASE"), expected("CONFIRM_PURCHASE")])
    assert result.summary["out_of_order"] == 1


def test_detects_protected_values_and_cost_fields():
    fake = FakeAudit(
        {
            ("PersonIdentity", "x"): [event("CREATE_PERSON_IDENTITY", "x", entity_type="PersonIdentity", company=None, sub="sub-admin", source="party-identity-service", new={"identification_number": "1023456789"})],
            ("Sale", "s"): [event("CONFIRM_SALE", "s", entity_type="Sale", source="sales-service", new={"lines": [{"cost_total": "100.00"}]})],
        }
    )
    result = checker(fake, protected_values={"1023456789"}).check(
        [
            expected("CREATE_PERSON_IDENTITY", "x", entity_type="PersonIdentity", scope="PLATFORM", actor="admin.test"),
            expected("CONFIRM_SALE", "s", entity_type="Sale"),
        ]
    )
    assert result.summary["protected"] == 1
    assert result.summary["cost_fields"] == 1
    assert not result.ok


def test_markers_are_not_protected_values():
    fake = FakeAudit({("PersonIdentity", "x"): [event("CREATE_PERSON_IDENTITY", "x", entity_type="PersonIdentity", company=None, sub="sub-admin", new={"identification_number": "<registrado>"})]})
    result = checker(fake, protected_values={"1023456789"}).check(
        [expected("CREATE_PERSON_IDENTITY", "x", entity_type="PersonIdentity", scope="PLATFORM", actor="admin.test")]
    )
    assert result.ok


def test_absence_of_an_action_is_verified():
    fake = FakeAudit({("Sale", "v5"): [event("CREATE_SALE", "v5", entity_type="Sale"), event("CONFIRM_SALE", "v5", entity_type="Sale", at="2026-10-09T10:05:00Z")]})
    result = checker(fake).check(
        [expected("CREATE_SALE", "v5", entity_type="Sale")],
        absences=[Absence("COMPANY", COMPANY, "Sale", "v5", "CONFIRM_SALE")],
    )
    assert result.summary["unexpected_present"] == 1
    assert not result.ok


def test_correlated_action_is_found_by_correlation_id():
    fake = FakeAudit(
        {("Purchase", "e-1"): [event("CONFIRM_PURCHASE", correlation="corr-1")]},
        by_correlation={"corr-1": []},
    )
    result = checker(fake).check([expected("CONFIRM_PURCHASE", correlation="corr-1")])
    assert result.summary["correlation_missing"] == 1
    fake.by_correlation["corr-1"] = [event("CONFIRM_PURCHASE", correlation="corr-1")]
    assert checker(fake).check([expected("CONFIRM_PURCHASE", correlation="corr-1")]).ok


def test_report_has_one_entry_per_entity(tmp_path):
    fake = FakeAudit({("Purchase", "e-1"): [event("CREATE_PURCHASE")]})
    result = checker(fake).check([expected("CREATE_PURCHASE")])
    path = result.write(tmp_path)
    import json

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["status"] == "OK"
    assert data["entities"][0]["entity_type"] == "Purchase"
    assert data["entities"][0]["expected"] == ["CREATE_PURCHASE"]


def test_actor_by_application_user_when_no_keycloak_sub():
    """Purchase y Sales identifican al autor con `application_user_id` (usuario operativo de la empresa)."""
    fake = FakeAudit({("Purchase", "e-1"): [dict(event("CREATE_PURCHASE", sub=None), application_user_id="au-compras")]})
    ok = checker(fake, application_users={"compras.test": "au-compras"}).check([expected("CREATE_PURCHASE")])
    assert ok.ok
    other = FakeAudit({("Purchase", "e-1"): [dict(event("CREATE_PURCHASE", sub=None), application_user_id="au-otro")]})
    wrong = checker(other, application_users={"compras.test": "au-compras"}).check([expected("CREATE_PURCHASE")])
    assert wrong.summary["wrong_actor"] == 1
    missing_actor = FakeAudit({("Purchase", "e-1"): [event("CREATE_PURCHASE", sub=None)]})
    assert checker(missing_actor).check([expected("CREATE_PURCHASE")]).summary["wrong_actor"] == 1


def test_failure_result_is_verified():
    failed = dict(event("CANCEL_PURCHASE"), result="FAILURE")
    fake = FakeAudit({("Purchase", "e-1"): [failed]})
    assert checker(fake).check([expected("CANCEL_PURCHASE", result="FAILURE")]).ok
    assert checker(fake).check([expected("CANCEL_PURCHASE")]).summary["wrong_result"] == 1
