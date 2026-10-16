"""Worker de entrega de solicitudes de precio (spec 021, EXC-001; T054; CP-T04, CP-37, CP-51).

Con un doble de Commercial Relationship: entrega en orden de secuencia por presentación, una presentación que falla no
detiene a las demás, espera creciente con tope, `409` sin reintento automático y `--check`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from purchase_service.application.ports import DeliveryResult
from purchase_service.application.price_update_delivery import PriceUpdateDeliveryService
from purchase_service.infrastructure.repository import PurchaseRepository
from tests.conftest import fetch, line

OUTBOX = "SELECT * FROM purchase_price_update_outbox ORDER BY sequence, created_at"


class FakeCommercial:
    def __init__(self) -> None:
        self.received: list[tuple[str, int]] = []
        self.answers: dict[str, list[DeliveryResult]] = {}

    def submit(self, company_id: UUID, payload: dict) -> DeliveryResult:
        presentation = payload["company_product_presentation_id"]
        queue = self.answers.get(presentation)
        result = queue.pop(0) if queue else DeliveryResult("ACCEPTED")
        if result.outcome == "ACCEPTED":
            self.received.append((presentation, payload["sequence"]))
        return result


def deliver(test_engine, gateway, *, interval: float = 0.0, max_backoff: float = 60.0) -> dict:
    with Session(test_engine, expire_on_commit=False) as session:
        service = PriceUpdateDeliveryService(
            PurchaseRepository(session, lock_timeout_ms=5000),
            gateway,
            interval_seconds=interval,
            max_backoff_seconds=max_backoff,
            clock=lambda: datetime.now(UTC),
        )
        return service.run_once()


def received_purchases(buyer, world, make_draft, confirm, receive, *specs):
    for quantity in specs:
        draft = make_draft(line(world.product, quantity, "1000", company_product_presentation_id=world.presentation),
                           line(world.product_2, quantity, "1000"))
        assert receive(confirm(draft).json()).status_code == 200


def test_delivers_in_sequence_order_one_head_per_presentation(buyer, world, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    make_sequence()
    received_purchases(buyer, world, make_draft, confirm, receive, "1", "2", "3")
    gateway = FakeCommercial()
    for _ in range(3):  # cada ciclo entrega solo la cabeza de cada presentación
        deliver(test_engine, gateway)
    by_presentation: dict[str, list[int]] = {}
    for presentation, sequence in gateway.received:
        by_presentation.setdefault(presentation, []).append(sequence)
    assert all(sequences == [1, 2, 3] for sequences in by_presentation.values()) and len(by_presentation) == 2
    assert {row["status"] for row in fetch(test_engine, OUTBOX)} == {"DELIVERED"}


def test_cpt04_a_failing_presentation_does_not_stop_the_others(buyer, world, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    make_sequence()
    received_purchases(buyer, world, make_draft, confirm, receive, "1", "2")
    gateway = FakeCommercial()
    gateway.answers[str(world.presentation)] = [DeliveryResult("RETRY", "COMMERCIAL_RELATIONSHIP_UNAVAILABLE")] * 5
    for _ in range(3):
        deliver(test_engine, gateway)
    rows = fetch(test_engine, OUTBOX)
    arroz = [row for row in rows if row["company_product_presentation_id"] == world.presentation]
    others = [row for row in rows if row["company_product_presentation_id"] != world.presentation]
    assert {row["status"] for row in others} == {"DELIVERED"}
    assert [row["status"] for row in arroz] == ["PENDING", "PENDING"]  # la segunda espera a la primera (orden)
    assert arroz[0]["attempts"] >= 1 and arroz[0]["last_error_code"] == "COMMERCIAL_RELATIONSHIP_UNAVAILABLE"
    assert arroz[1]["attempts"] == 0


def test_backoff_grows_and_respects_the_cap(buyer, world, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    make_sequence()
    received_purchases(buyer, world, make_draft, confirm, receive, "1")
    gateway = FakeCommercial()
    gateway.answers[str(world.presentation)] = [DeliveryResult("RETRY", "HTTP_503")]
    deliver(test_engine, gateway, interval=10, max_backoff=15)
    [row] = [row for row in fetch(test_engine, OUTBOX) if row["company_product_presentation_id"] == world.presentation]
    wait = (row["next_attempt_at"] - row["last_error_at"]).total_seconds()
    assert 14 <= wait <= 16  # 10 × 2¹ = 20, limitado a 15


def test_conflict_is_not_retried_automatically(buyer, world, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    make_sequence()
    received_purchases(buyer, world, make_draft, confirm, receive, "1")
    gateway = FakeCommercial()
    gateway.answers[str(world.presentation)] = [DeliveryResult("REJECTED", "SEQUENCE_CONFLICT")]
    deliver(test_engine, gateway)
    deliver(test_engine, gateway)
    [row] = [row for row in fetch(test_engine, OUTBOX) if row["company_product_presentation_id"] == world.presentation]
    assert row["status"] == "PENDING" and row["attempts"] == 1 and row["last_error_code"] == "SEQUENCE_CONFLICT"
    assert row["next_attempt_at"].year > datetime.now(UTC).year + 50


def test_worker_check_reports_health(monkeypatch, test_database_url) -> None:
    from purchase_service import price_update_worker

    monkeypatch.setenv("DATABASE_URL", test_database_url)
    assert price_update_worker.main(["--check"]) == 0
