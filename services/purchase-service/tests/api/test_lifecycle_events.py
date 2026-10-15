"""Hitos logísticos (Historia 4; FR-035 a FR-038, DS-08, RN-09, RN-10; T057)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from tests.conftest import base, fetch, user_sub


def at(hours_ago: float) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours_ago)).isoformat()


def record(client, world, purchase, event_type: str, hours_ago: float, source: str = "USER", notes=None):
    return client.post(
        f"{base(world)}/purchases/{purchase['id']}/lifecycle-events",
        json={"event_type": event_type, "occurred_at": at(hours_ago), "source": source, "notes": notes},
    )


def test_full_timeline_with_intervals(buyer, world, fakes, make_sequence, make_draft, confirm, receive) -> None:
    make_sequence()
    draft = make_draft()
    assert record(buyer, world, draft, "ORDERED", 72).status_code == 201
    assert record(buyer, world, draft, "SUPPLIER_DISPATCHED", 48, source="SUPPLIER").status_code == 201
    confirmed = confirm(draft).json()
    assert record(buyer, world, confirmed, "ARRIVED", 24).status_code == 201
    confirmed = receive(confirmed).json()  # spec 020: el hito RECEIVED exige la recepción física
    received = record(buyer, world, confirmed, "RECEIVED", 22, notes="Recibido conforme")
    assert received.status_code == 201
    event = received.json()
    assert event["recorded_by_user_id"] == str(fakes.oc.members[(user_sub("compras.test"), world.company)])
    assert event["created_by"] == user_sub("compras.test") and event["notes"] == "Recibido conforme"
    assert record(buyer, world, confirmed, "AVAILABLE_FOR_SALE", 20).status_code == 201

    timeline = buyer.get(f"{base(world)}/purchases/{draft['id']}/lifecycle-events").json()
    assert [item["event_type"] for item in timeline["items"]] == [
        "ORDERED", "SUPPLIER_DISPATCHED", "ARRIVED", "RECEIVED", "AVAILABLE_FOR_SALE"
    ]
    assert all(item["is_current"] for item in timeline["items"])
    assert [(item["from"], item["to"], item["hours"]) for item in timeline["intervals"]] == [
        ("ORDERED", "SUPPLIER_DISPATCHED", "24.00"),
        ("SUPPLIER_DISPATCHED", "ARRIVED", "24.00"),
        ("ARRIVED", "RECEIVED", "2.00"),
        ("RECEIVED", "AVAILABLE_FOR_SALE", "2.00"),
    ]
    assert timeline["total_lead_time_hours"] == "52.00"


def test_out_of_order_and_future_are_422(buyer, world, make_draft) -> None:
    draft = make_draft()
    ordered = record(buyer, world, draft, "ORDERED", 10).json()
    response = record(buyer, world, draft, "ARRIVED", 11)
    assert response.status_code == 422
    error = response.json()["errors"][0]
    assert error["code"] == "EVENT_OUT_OF_ORDER" and error["conflicting_event_id"] == ordered["id"]
    assert error["conflicting_event_type"] == "ORDERED"
    assert record(buyer, world, draft, "ARRIVED", -1).json()["errors"][0]["code"] == "EVENT_IN_FUTURE"
    assert record(buyer, world, draft, "ARRIVED", -0.05).status_code == 201  # tolerancia de 5 minutos


def test_reception_needs_confirmed_and_cancelled_admits_none(buyer, world, make_draft, cancel) -> None:
    draft = make_draft()
    for event_type in ("RECEIVED", "AVAILABLE_FOR_SALE"):
        response = record(buyer, world, draft, event_type, 1)
        assert response.status_code == 409 and response.json()["code"] == "PURCHASE.EVENT_NOT_ALLOWED_IN_STATUS"
    cancelled = cancel(draft).json()
    response = record(buyer, world, cancelled, "ORDERED", 1)
    assert response.status_code == 409


def test_correction_keeps_history_and_changes_current(buyer, world, make_draft) -> None:
    draft = make_draft()
    wrong = record(buyer, world, draft, "ORDERED", 2).json()
    record(buyer, world, draft, "ARRIVED", 1)
    corrected = record(buyer, world, draft, "ORDERED", 5).json()
    timeline = buyer.get(f"{base(world)}/purchases/{draft['id']}/lifecycle-events").json()
    assert timeline["current"]["ORDERED"] == corrected["id"]
    flags = {item["id"]: item["is_current"] for item in timeline["items"]}
    assert flags[wrong["id"]] is False and flags[corrected["id"]] is True
    assert len(timeline["items"]) == 3


def test_recording_does_not_change_purchase_version(buyer, world, make_draft) -> None:
    draft = make_draft()
    record(buyer, world, draft, "ORDERED", 1)
    assert buyer.get(f"{base(world)}/purchases/{draft['id']}").json()["version"] == draft["version"]


def test_never_writes_commercial_relationship(buyer, world, fakes, make_draft) -> None:
    draft = make_draft()
    fakes.cr.availability.fail_if_called = True
    assert record(buyer, world, draft, "ORDERED", 1).status_code == 201


def test_permissions_and_assignment(as_user, buyer, world, fakes, make_draft) -> None:
    draft = make_draft()
    assert record(as_user("reportes.test"), world, draft, "ORDERED", 1).status_code == 403
    assert as_user("reportes.test").get(f"{base(world)}/purchases/{draft['id']}/lifecycle-events").status_code == 200
    fakes.oc.assignments.discard((user_sub("compras.test"), world.branch))
    assert record(buyer, world, draft, "ORDERED", 1).status_code == 403


def test_invalid_body(buyer, world, make_draft) -> None:
    draft = make_draft()
    url = f"{base(world)}/purchases/{draft['id']}/lifecycle-events"
    assert buyer.post(url, json={"event_type": "SHIPPED", "occurred_at": at(1), "source": "USER"}).status_code == 422
    assert buyer.post(url, json={"event_type": "ORDERED", "occurred_at": "2026-10-06T10:00:00", "source": "USER"}).status_code == 422
    assert buyer.post(url, json={"event_type": "ORDERED", "occurred_at": at(1), "source": "OTRO"}).status_code == 422


def test_events_are_audited(buyer, world, make_draft, test_engine) -> None:
    draft = make_draft()
    record(buyer, world, draft, "ORDERED", 1)
    actions = [row["payload"]["action"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox")]
    assert actions.count("RECORD_PURCHASE_LIFECYCLE_EVENT") == 1


def test_receipt_milestones_require_the_physical_receipt(buyer, world, make_sequence, make_draft, confirm) -> None:
    """Spec 020 (FR-020-07): RECEIVED y AVAILABLE_FOR_SALE solo en compras recibidas."""
    make_sequence()
    confirmed = confirm(make_draft()).json()
    for event_type in ("RECEIVED", "AVAILABLE_FOR_SALE"):
        response = record(buyer, world, confirmed, event_type, 1)
        assert response.status_code == 409 and response.json()["code"] == "PURCHASE.PURCHASE_NOT_RECEIVED"
    assert record(buyer, world, confirmed, "ARRIVED", 1).status_code == 201
