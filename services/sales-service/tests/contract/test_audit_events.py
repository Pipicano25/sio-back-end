"""Auditoría por Transactional Outbox (FR-031; research.md R-13; SC-007; DS-12; T070)."""

from __future__ import annotations

from tests.conftest import base, count_rows, fetch, line, new_key, sequence_body


def events(test_engine) -> list[dict]:
    return [row["payload"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox ORDER BY created_at")]


def test_every_action_writes_exactly_one_event(seller, world, fakes, make_draft, confirm, cancel, test_engine) -> None:
    sequence = seller.post(f"{base(world)}/sale-sequences", json=sequence_body()).json()
    draft = make_draft()
    url = f"{base(world)}/sales/{draft['id']}"
    added = seller.post(f"{url}/details", json={**line(world.product_2), "version": 1}).json()
    updated = seller.put(f"{url}/details/{added['lines'][1]['id']}", json={**line(world.product_2, "2"), "version": 2}).json()
    deleted = seller.delete(f"{url}/details/{added['lines'][1]['id']}", params={"version": updated["version"]}).json()
    header = {"branch_id": str(world.branch), "company_customer_id": str(world.customer), "payment_method_id": str(world.payment_method)}
    edited = seller.put(url, json={**header, "version": deleted["version"]}).json()
    confirmed = confirm(edited).json()
    cancel(confirmed)
    seq_url = f"{base(world)}/sale-sequences/{sequence['id']}"
    changed = seller.put(seq_url, json={**sequence_body(maximum_number=99), "version": 1}).json()
    off = seller.post(f"{seq_url}/deactivate", json={"version": changed["version"]}).json()
    seller.post(f"{seq_url}/reactivate", json={"version": off["version"]})

    actions = [event["action"] for event in events(test_engine)]
    assert sorted(actions) == sorted([
        "CREATE_SALE_SEQUENCE", "CREATE_SALE", "ADD_SALE_DETAIL", "UPDATE_SALE_DETAIL",
        "DELETE_SALE_DETAIL", "UPDATE_SALE", "CONFIRM_SALE",
        "CANCEL_SALE", "UPDATE_SALE_SEQUENCE", "DEACTIVATE_SALE_SEQUENCE", "REACTIVATE_SALE_SEQUENCE",
    ])
    for event in events(test_engine):
        assert event["company_id"] == str(world.company)
        assert event["result"] == "SUCCESS"
        assert event["entity_type"] in {"Sale", "SaleDetail", "SaleSequence"}


def test_confirmation_event_carries_correlation(seller, world, make_sequence, make_draft, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    correlation = "0b6f1d1c-1c39-4f4f-9a7d-7f1a2b3c4d5e"
    seller.post(
        f"{base(world)}/sales/{draft['id']}/confirmation",
        json={"version": 1},
        headers={"Idempotency-Key": new_key(), "X-Correlation-Id": correlation},
    )
    confirm_event = next(event for event in events(test_engine) if event["action"] == "CONFIRM_SALE")
    assert confirm_event["correlation_id"] == correlation


def test_rejections_before_effects_write_no_event(seller, world, make_draft, confirm, test_engine) -> None:
    draft = make_draft()
    before = count_rows(test_engine, "audit_outbox")
    confirm(draft)  # sin secuencia → 409 antes de efectos
    seller.post(f"{base(world)}/sales", json={"branch_id": "x"})
    seller.post(f"{base(world)}/sales/{draft['id']}/details", json={**line(world.product_no_inventory), "version": 1})
    assert count_rows(test_engine, "audit_outbox") == before


def test_failures_with_registered_operation_are_audited_as_failure(world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    fakes.inventory.reject_output = (422, "VALIDATION_ERROR")
    confirm(make_draft())
    failure = [event for event in events(test_engine) if event["action"] == "CONFIRM_SALE"]
    assert len(failure) == 1 and failure[0]["result"] == "FAILURE"


def test_no_sensitive_values_in_events(seller, world, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    key = new_key()
    draft = make_draft()
    confirm(draft, key)
    assert key not in str(events(test_engine))


def test_events_never_carry_cost_or_margin(supervisor, world, fakes, make_sequence, make_draft, confirm, cancel, test_engine) -> None:
    """DS-12: Audit no aplica el permiso de rentabilidad; los eventos no llevan costo ni margen."""
    make_sequence()
    draft = make_draft(line(world.product, "3"), line(world.product_2, "1"))
    confirmed = confirm(draft).json()
    cancel(confirmed)
    payloads = str(events(test_engine))
    for word in ("unit_cost", "cost_total", "cost_known", "gross_margin", "has_unknown_cost", "movement_value"):
        assert word not in payloads, word


def test_rollback_leaves_no_event(seller, world, fakes, make_sequence, make_draft, confirm, test_engine) -> None:
    make_sequence()
    draft = make_draft()
    before = count_rows(test_engine, "audit_outbox")
    fakes.inventory.availability.down = True
    confirm(draft)  # T1 se confirma, la salida no: queda PENDING sin evento de confirmación
    assert [event["action"] for event in events(test_engine)][before:] == []
