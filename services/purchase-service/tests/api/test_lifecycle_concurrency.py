"""Hitos concurrentes incompatibles de la misma compra (R-10; T058)."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

from tests.conftest import base, count_rows


def test_incompatible_concurrent_events_are_serialized(test_client, user_token, world, make_draft, test_engine) -> None:
    draft = make_draft()
    now = datetime.now(UTC)
    # Cada uno es válido por sí solo; juntos son incompatibles (ARRIVED antes que ORDERED).
    bodies = [
        {"event_type": "ORDERED", "occurred_at": (now - timedelta(hours=1)).isoformat(), "source": "USER"},
        {"event_type": "ARRIVED", "occurred_at": (now - timedelta(hours=2)).isoformat(), "source": "USER"},
    ]
    barrier = threading.Barrier(2)
    statuses: list[int] = []

    def send(body) -> None:
        barrier.wait(5)
        response = test_client.post(
            f"{base(world)}/purchases/{draft['id']}/lifecycle-events",
            json=body,
            headers={"Authorization": f"Bearer {user_token('compras.test')}"},
        )
        statuses.append(response.status_code)

    threads = [threading.Thread(target=send, args=(body,)) for body in bodies]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(20)
    assert sorted(statuses) == [201, 422]
    assert count_rows(test_engine, "purchase_lifecycle_events") == 1
