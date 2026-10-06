"""Ciclo del worker con `httpx.MockTransport` (R-11; RC-04, RC-05; T052)."""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from sio_audit.event import AuditEvent
from sio_audit.outbox import record_audit_event
from sio_audit.worker.loop import AuditClient, run_once
from sio_audit.worker.settings import WorkerSettings

TOKEN_URL = "http://keycloak.test/realms/sio/protocol/openid-connect/token"
BATCH_URL = "http://audit.test/api/v1/audit-events/batch"
SECRET = "valor-secreto-original"


def settings(outbox_database_url: str, **changes) -> WorkerSettings:
    values = dict(
        database_url=outbox_database_url,
        audit_base_url="http://audit.test/api/v1",
        keycloak_base_url="http://keycloak.test",
        keycloak_realm="sio",
        client_id="emisor-prueba",
        client_secret="secreto-de-prueba",
        backoff_initial_seconds=1.0,
        backoff_factor=2.0,
        backoff_max_seconds=300.0,
        batch_size=100,
    )
    values.update(changes)
    return WorkerSettings(**values)


class FakeAudit:
    """Keycloak y Audit simulados; `responder(events)` decide la respuesta del lote."""

    def __init__(self, responder) -> None:
        self.responder = responder
        self.batches: list[list[dict]] = []
        self.token_requests = 0
        self.tokens_issued = 0

    def handler(self, request: httpx.Request) -> httpx.Response:
        if str(request.url) == TOKEN_URL:
            self.token_requests += 1
            self.tokens_issued += 1
            return httpx.Response(200, json={"access_token": f"tok-{self.tokens_issued}", "expires_in": 300})
        assert str(request.url) == BATCH_URL
        events = json.loads(request.content)["events"]
        self.batches.append(events)
        return self.responder(events, request)


def ok(events, request=None) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "items": [
                {"index": i, "event_id": e["event_id"], "id": str(uuid4()), "outcome": "CREATED"}
                for i, e in enumerate(events)
            ]
        },
    )


def seed(engine, count: int, **changes) -> list[str]:
    ids = []
    with Session(engine) as session:
        for _ in range(count):
            event = AuditEvent(
                event_id=uuid4(),
                company_id=uuid4(),
                action="CREATE",
                entity_type="Sale",
                result="SUCCESS",
                occurred_at=datetime.now(UTC),
                new_values=changes.get("new_values", {"total": "1.00"}),
            )
            ids.append(str(record_audit_event(session, event)))
        session.commit()
    return ids


def state(engine) -> dict[str, tuple]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT event_id::text, status, attempts, last_status_code, last_error_code, "
                "sent_at IS NOT NULL AS sent, EXTRACT(EPOCH FROM next_attempt_at - now()) AS wait "
                "FROM audit_outbox"
            )
        ).all()
    return {row[0]: tuple(row[1:]) for row in rows}


def run(engine, url, audit: FakeAudit, **changes):
    current = settings(url, **changes)
    client = AuditClient(current, transport=httpx.MockTransport(audit.handler))
    return run_once(engine, client, current)


def test_confirmation_marks_sent(clean_outbox, outbox_database_url) -> None:
    ids = seed(clean_outbox, 3)
    audit = FakeAudit(ok)

    result = run(clean_outbox, outbox_database_url, audit)

    assert sorted(result.sent) == sorted(ids)
    assert all(row[0] == "SENT" and row[4] for row in state(clean_outbox).values())
    assert [event["event_id"] for event in audit.batches[0]] and len(audit.batches) == 1
    # Sin pendientes: el siguiente ciclo no envía nada.
    assert run(clean_outbox, outbox_database_url, audit).selected == 0


def test_already_exists_is_confirmation(clean_outbox, outbox_database_url) -> None:
    seed(clean_outbox, 1)

    def exists(events, request):
        return httpx.Response(200, json={"items": [{"index": 0, "event_id": events[0]["event_id"], "id": str(uuid4()), "outcome": "ALREADY_EXISTS"}]})

    run(clean_outbox, outbox_database_url, FakeAudit(exists))
    assert next(iter(state(clean_outbox).values()))[0] == "SENT"


@pytest.mark.parametrize(
    "responder",
    [
        lambda events, request: httpx.Response(503, json={"code": "AUDIT.DEPENDENCY_UNAVAILABLE"}),
        lambda events, request: httpx.Response(500, text="x"),
        lambda events, request: httpx.Response(408),
        lambda events, request: httpx.Response(429),
    ],
)
def test_retryable_responses_backoff(clean_outbox, outbox_database_url, responder) -> None:
    seed(clean_outbox, 2)

    result = run(clean_outbox, outbox_database_url, FakeAudit(responder))

    assert len(result.retried) == 2 and not result.sent
    for status, attempts, code, error, sent, wait in state(clean_outbox).values():
        assert status == "PENDING" and attempts == 1 and not sent
        assert 0.8 <= float(wait) <= 1.2  # initial * factor^0 con jitter ±10 %


@pytest.mark.parametrize("exc", [httpx.ConnectError("x"), httpx.ReadTimeout("x")])
def test_network_errors_backoff(clean_outbox, outbox_database_url, exc) -> None:
    seed(clean_outbox, 1)

    def fail(events, request):
        raise exc

    result = run(clean_outbox, outbox_database_url, FakeAudit(fail))
    assert result.retried and next(iter(state(clean_outbox).values()))[0] == "PENDING"


def test_backoff_grows_and_is_capped(clean_outbox, outbox_database_url) -> None:
    [event_id] = seed(clean_outbox, 1)
    unavailable = FakeAudit(lambda events, request: httpx.Response(503))
    expected = [1, 2, 4, 8, 10, 10]

    for attempt, base in enumerate(expected, start=1):
        with clean_outbox.begin() as connection:
            connection.execute(text("UPDATE audit_outbox SET next_attempt_at = now()"))
        run(clean_outbox, outbox_database_url, unavailable, backoff_max_seconds=10.0)
        status, attempts, *_rest, wait = state(clean_outbox)[event_id]
        assert attempts == attempt
        assert base * 0.85 <= float(wait) <= min(base * 1.15, 10.0)


def test_rejected_events_do_not_block_others(clean_outbox, outbox_database_url, caplog) -> None:
    caplog.set_level(logging.INFO, logger="sio_audit")
    ids = seed(clean_outbox, 4, new_values={"password": SECRET})

    def responder(events, request):
        if len(events) == 4:
            return httpx.Response(
                409,
                json={"code": "AUDIT.EVENT_ID_CONFLICT", "conflicts": [{"index": 1, "event_id": events[1]["event_id"]}]},
            )
        if len(events) == 3:
            return httpx.Response(
                422,
                json={"code": "AUDIT.VALIDATION_ERROR", "errors": [{"field": "events[2].action", "message": "x"}]},
            )
        return ok(events)

    audit = FakeAudit(responder)
    result = run(clean_outbox, outbox_database_url, audit)

    rows = state(clean_outbox)
    rejected = {ids[1], ids[3]}
    assert set(result.rejected) == rejected
    assert set(result.sent) == {ids[0], ids[2]}
    for event_id in rejected:
        status, attempts, code, error, sent, wait = rows[event_id]
        assert status == "PENDING" and not sent and float(wait) > 250
    assert [len(batch) for batch in audit.batches] == [4, 3, 2]
    assert SECRET not in caplog.text
    assert ids[1] in caplog.text


def test_401_renews_token_once(clean_outbox, outbox_database_url) -> None:
    seed(clean_outbox, 1)
    calls = {"n": 0}

    def responder(events, request):
        calls["n"] += 1
        if request.headers["authorization"] == "Bearer tok-1":
            return httpx.Response(401)
        return ok(events)

    audit = FakeAudit(responder)
    result = run(clean_outbox, outbox_database_url, audit)

    assert result.sent and audit.token_requests == 2 and calls["n"] == 2


@pytest.mark.parametrize("status", [401, 403])
def test_identity_rejections_use_max_backoff(clean_outbox, outbox_database_url, status) -> None:
    seed(clean_outbox, 1)
    result = run(clean_outbox, outbox_database_url, FakeAudit(lambda events, request: httpx.Response(status)))

    assert result.rejected and not result.sent
    assert float(next(iter(state(clean_outbox).values()))[5]) > 250


def test_token_unavailable_is_retry(clean_outbox, outbox_database_url) -> None:
    seed(clean_outbox, 1)

    def handler(request):
        return httpx.Response(503)

    current = settings(outbox_database_url)
    result = run_once(clean_outbox, AuditClient(current, transport=httpx.MockTransport(handler)), current)
    assert result.retried and not result.sent


def test_unconfirmed_items_stay_pending(clean_outbox, outbox_database_url) -> None:
    ids = seed(clean_outbox, 2)

    def partial(events, request):
        return httpx.Response(200, json={"items": [{"index": 0, "event_id": events[0]["event_id"], "id": str(uuid4()), "outcome": "CREATED"}]})

    run(clean_outbox, outbox_database_url, FakeAudit(partial))
    rows = state(clean_outbox)
    assert sorted(row[0] for row in rows.values()) == ["PENDING", "SENT"]
    assert len(ids) == 2


def test_never_deletes_rows(clean_outbox, outbox_database_url) -> None:
    seed(clean_outbox, 3)
    run(clean_outbox, outbox_database_url, FakeAudit(ok))
    assert len(state(clean_outbox)) == 3


def test_resumes_pending_after_restart(clean_outbox, outbox_database_url) -> None:
    ids = seed(clean_outbox, 2)
    run(clean_outbox, outbox_database_url, FakeAudit(lambda events, request: httpx.Response(503)))

    with clean_outbox.begin() as connection:
        connection.execute(text("UPDATE audit_outbox SET next_attempt_at = now()"))

    # Un worker nuevo (otro proceso) retoma lo pendiente desde la tabla.
    result = run(clean_outbox, outbox_database_url, FakeAudit(ok))
    assert sorted(result.sent) == sorted(ids)


def test_concurrent_cycles_never_send_the_same_row(clean_outbox, outbox_database_url) -> None:
    ids = seed(clean_outbox, 40)
    barrier = threading.Barrier(2)
    seen: list[str] = []
    lock = threading.Lock()

    def slow_ok(events, request):
        with lock:
            seen.extend(event["event_id"] for event in events)
        return ok(events)

    def cycle() -> None:
        barrier.wait()
        run(clean_outbox, outbox_database_url, FakeAudit(slow_ok), batch_size=25)

    threads = [threading.Thread(target=cycle) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(seen) == len(set(seen)) == 40
    assert sorted(seen) == sorted(ids)
