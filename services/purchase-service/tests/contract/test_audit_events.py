"""Auditoría por Transactional Outbox (FR-044; research.md R-13; SC-007; T064)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.conftest import base, count_rows, fetch, line, new_key, sequence_body


def events(test_engine) -> list[dict]:
    return [row["payload"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox ORDER BY created_at")]


def test_every_action_writes_exactly_one_event(buyer, world, fakes, make_draft, confirm, cancel, test_engine) -> None:
    sequence = buyer.post(f"{base(world)}/purchase-sequences", json=sequence_body()).json()
    draft = make_draft()
    url = f"{base(world)}/purchases/{draft['id']}"
    added = buyer.post(f"{url}/details", json={**line(world.product_2), "version": 1}).json()
    updated = buyer.put(f"{url}/details/{added['lines'][1]['id']}", json={**line(world.product_2, "2"), "version": 2}).json()
    deleted = buyer.delete(f"{url}/details/{added['lines'][1]['id']}", params={"version": updated["version"]}).json()
    header = {"branch_id": str(world.branch), "company_supplier_id": str(world.supplier), "operation_date": draft["operation_date"]}
    edited = buyer.put(url, json={**header, "version": deleted["version"]}).json()
    buyer.post(f"{url}/lifecycle-events", json={"event_type": "ORDERED", "occurred_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(), "source": "USER"})
    confirmed = confirm(edited).json()
    cancel(confirmed)
    seq_url = f"{base(world)}/purchase-sequences/{sequence['id']}"
    changed = buyer.put(seq_url, json={**sequence_body(maximum_number=99), "version": 1}).json()
    off = buyer.post(f"{seq_url}/deactivate", json={"version": changed["version"]}).json()
    buyer.post(f"{seq_url}/reactivate", json={"version": off["version"]})

    actions = [event["action"] for event in events(test_engine)]
    assert sorted(actions) == sorted([
        "CREATE_PURCHASE_SEQUENCE", "CREATE_PURCHASE", "ADD_PURCHASE_DETAIL", "UPDATE_PURCHASE_DETAIL",
        "DELETE_PURCHASE_DETAIL", "UPDATE_PURCHASE", "RECORD_PURCHASE_LIFECYCLE_EVENT", "CONFIRM_PURCHASE",
        "CANCEL_PURCHASE", "UPDATE_PURCHASE_SEQUENCE", "DEACTIVATE_PURCHASE_SEQUENCE", "REACTIVATE_PURCHASE_SEQUENCE",
    ])
    for event in events(test_engine):
        assert event["company_id"] == str(world.company)
        assert event["result"] == "SUCCESS"
        assert event["entity_type"] in {"Purchase", "PurchaseDetail", "PurchaseLifecycleEvent", "PurchaseSequence"}


def test_confirmation_event_carries_correlation(buyer, world, make_sequence, make_draft, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    correlation = "0b6f1d1c-1c39-4f4f-9a7d-7f1a2b3c4d5e"
    buyer.post(
        f"{base(world)}/purchases/{draft['id']}/confirmation",
        json={"version": 1},
        headers={"Idempotency-Key": new_key(), "X-Correlation-Id": correlation},
    )
    confirm_event = next(event for event in events(test_engine) if event["action"] == "CONFIRM_PURCHASE")
    assert confirm_event["correlation_id"] == correlation


def test_rejections_before_effects_write_no_event(buyer, world, make_draft, confirm, test_engine) -> None:
    draft = make_draft()
    before = count_rows(test_engine, "audit_outbox")
    confirm(draft)  # sin secuencia → 409 antes de efectos
    buyer.post(f"{base(world)}/purchases", json={"branch_id": "x"})
    buyer.post(f"{base(world)}/purchases/{draft['id']}/details", json={**line(world.product_no_inventory), "version": 1})
    assert count_rows(test_engine, "audit_outbox") == before


def test_failures_with_registered_operation_are_audited_as_failure(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    fakes.inventory.reject_entry = (422, "VALIDATION_ERROR")
    confirm(make_draft())
    failure = [event for event in events(test_engine) if event["action"] == "CONFIRM_PURCHASE"]
    assert len(failure) == 1 and failure[0]["result"] == "FAILURE"


def test_no_sensitive_values_in_events(buyer, world, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    key = new_key()
    draft = make_draft()
    confirm(draft, key)
    assert key not in str(events(test_engine))
