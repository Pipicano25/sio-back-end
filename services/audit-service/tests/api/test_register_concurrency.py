"""Idempotencia bajo reenvíos secuenciales y concurrentes (RC-05, SC-002; T027)."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import text

from tests.conftest import event_body

URL = "/api/v1/audit-events"
TOTAL = 1000
PARALLEL = 20


def test_thousand_resends_leave_one_row(emitter, test_engine) -> None:
    body = event_body()
    statuses: list[int] = []
    ids: set[str] = set()

    def send() -> None:
        response = emitter.post(URL, json=body)
        statuses.append(response.status_code)
        ids.add(response.json()["id"])

    # Primera tanda simultánea (carrera de inserción) y el resto secuencial y en tandas.
    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        for _ in range(TOTAL // PARALLEL):
            list(pool.map(lambda _: send(), range(PARALLEL)))

    assert len(statuses) == TOTAL
    assert set(statuses) <= {200, 201}
    assert statuses.count(201) == 1
    assert len(ids) == 1

    with test_engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM audit_events")).scalar_one() == 1
