"""Orden por secuencia, independencia por lista y reintentos (T052; FR-021-22, FR-021-26; RC-021-5, RC-021-8).

CP-37 (dos recepciones en orden), CP-51 (falta la secuencia anterior: CR espera), CP-T05 (`received_at` inverso a la
secuencia), CP-39 (un fallo en una lista no impide las demás), CP-17 y CP-49 (el reintento usa la captura), CP-48
(reintentar una aplicación completada no crea historial), CP-T09 (dos workers a la vez no duplican) y CP-06 (otra
empresa nunca interviene). Datos ficticios.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from commercial_relationship_service.application import automatic_price_application_service as processing
from commercial_relationship_service.infrastructure.pricing_repositories import AutomaticPricingRepository
from commercial_relationship_service.price_worker import run_cycle
from tests.api.automatic_pricing_helpers import (
    add_presentation,
    applications,
    current_price,
    policy,
    prices,
    request_body,
    run_worker,
    scenario,
    submit,
    technical,
)
from tests.api.helpers import create_price_list
from tests.api.test_automatic_price_applications import force_failure

D = Decimal
SECOND = ("30000.00", "10.0000")  # 3.000 por unidad


@pytest.fixture
def supervisor(as_user):
    return as_user("supervisor.test")


@pytest.fixture
def client(as_token, service_token):
    return technical(as_token, service_token)


def due_now(test_engine, application_id) -> None:
    """Adelanta el reintento programado (la espera creciente ya se prueba en `test_automatic_price_processing.py`)."""
    with test_engine.begin() as connection:
        connection.execute(
            text("UPDATE automatic_price_applications SET next_attempt_at = now() WHERE id = :id"), {"id": application_id}
        )


def test_cp37_two_receipts_in_order(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation], markup="30")
    submit(client, world, request_body(world, sequence=1))
    submit(client, world, request_body(world, sequence=2, line_total="20000.00", previous=("23800.00", "10.0000")))
    run_worker(test_engine)
    first, second = applications(test_engine)
    assert (first["sequence"], first["status"], first["new_price"]) == (1, "APPLIED", D("3094.00"))
    # 2.000 < 2.380: promedio simple 2.190 × 1,30 = 2.847
    assert (second["sequence"], second["status"], second["new_price"]) == (2, "APPLIED", D("2847.00"))
    assert second["completed_at"] >= first["completed_at"]
    assert current_price(test_engine, world) == D("2847.00")


def test_cp51_waits_for_the_missing_previous_sequence(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation], markup="30")
    second_body = request_body(world, sequence=2, line_total=SECOND[0], previous=("23800.00", "10.0000"))
    submit(client, world, second_body)
    run_worker(test_engine)
    [waiting] = applications(test_engine)
    assert waiting["status"] == "PENDING" and waiting["attempts"] == 0  # espera la secuencia 1
    assert current_price(test_engine, world) is None

    submit(client, world, request_body(world, sequence=1))
    run_worker(test_engine)
    assert [(row["sequence"], row["status"]) for row in applications(test_engine)] == [(1, "APPLIED"), (2, "APPLIED")]
    assert current_price(test_engine, world) == D("3900.00")  # rige la última secuencia


def test_cpt05_received_at_inverse_to_the_sequence(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation], markup="30")
    later = datetime.now(UTC) + timedelta(minutes=2)
    submit(client, world, request_body(world, sequence=1, received_at=later))
    submit(client, world, request_body(world, sequence=2, line_total=SECOND[0], previous=("23800.00", "10.0000"),
                                       received_at=later - timedelta(minutes=1)))
    run_worker(test_engine)
    first, second = applications(test_engine)
    assert (first["sequence"], second["sequence"]) == (1, 2)
    assert second["completed_at"] >= first["completed_at"]  # se procesa por secuencia, no por received_at
    assert current_price(test_engine, world) == D("3900.00")


def test_cp39_a_failing_list_does_not_block_the_others(supervisor, client, company, fake_catalog, test_engine, monkeypatch, outbox) -> None:
    world = scenario(supervisor, company, fake_catalog)
    mayorista = create_price_list(supervisor, company, code="MAY-FICTICIA")
    especial = create_price_list(supervisor, company, code="ESP-FICTICIA")
    policy(supervisor, world, [world.presentation], markup="30")
    policy(supervisor, world, [world.presentation], markup="20", price_list=mayorista)
    policy(supervisor, world, [world.presentation], markup="50", price_list=especial)

    original = processing.final_price

    def failing(reference, markup, currency):
        if Decimal(markup) == D("50"):
            raise RuntimeError("Fallo simulado de la lista Especial")
        return original(reference, markup, currency)

    monkeypatch.setattr(processing, "final_price", failing)
    submit(client, world, request_body(world))
    run_worker(test_engine)
    by_list = {str(row["price_list_id"]): row for row in applications(test_engine)}
    assert by_list[world.price_list["id"]]["status"] == "APPLIED"
    assert by_list[mayorista["id"]]["status"] == "APPLIED"
    assert by_list[especial["id"]]["status"] == "FAILED"
    assert current_price(test_engine, world) == D("3094.00")
    assert current_price(test_engine, world, price_list=mayorista) == D("2856.00")
    assert current_price(test_engine, world, price_list=especial) is None
    failed = by_list[especial["id"]]
    assert failed["attempts"] >= 1 and failed["next_attempt_at"] > failed["first_attempt_at"]
    assert failed["last_error_code"] == "RuntimeError" and "Especial" in failed["last_error_detail"]
    fails = [event for event in outbox() if event["action"] == "FAIL_AUTOMATIC_PRICE"]
    # T056: se audita el primer fallo y cada cambio de error, no cada reintento con el mismo error
    assert len(fails) == 1 and fails[0]["entity_id"] == str(failed["id"])
    assert fails[0]["username_snapshot"] == "commercial-relationship-price-worker"

    monkeypatch.setattr(processing, "final_price", original)
    due_now(test_engine, by_list[especial["id"]]["id"])
    time.sleep(0.05)
    run_worker(test_engine)
    after = {str(row["price_list_id"]): row for row in applications(test_engine)}
    assert after[especial["id"]]["status"] == "APPLIED" and after[especial["id"]]["attempts"] >= 2
    assert after[world.price_list["id"]]["attempts"] == 1 and after[mayorista["id"]]["attempts"] == 1  # solo Especial
    assert current_price(test_engine, world, price_list=especial) == D("3570.00")


@pytest.mark.parametrize("change", ["percentage", "deactivate"])
def test_cp17_cp49_a_retry_uses_the_capture(supervisor, client, company, fake_catalog, test_engine, change) -> None:
    world = scenario(supervisor, company, fake_catalog)
    created = policy(supervisor, world, [world.presentation], markup="30")
    submit(client, world, request_body(world))
    [row] = applications(test_engine)
    force_failure(test_engine, row["id"])
    if change == "percentage":
        response = supervisor.post(f"/api/v1/pricing-policies/{created['id']}/percentage",
                                   json={"version": created["version"], "markup_percentage": "50"})
    else:
        response = supervisor.post(f"/api/v1/pricing-policies/{created['id']}/deactivate",
                                   json={"version": created["version"], "reason": "Fin de la política (ficticio)"})
    assert response.status_code == 200, response.text
    due_now(test_engine, row["id"])
    run_worker(test_engine)
    [done] = applications(test_engine)
    assert done["status"] == "APPLIED" and done["markup_percentage"] == D("30.0000")
    assert current_price(test_engine, world) == D("3094.00")  # 30 % capturado, no 50 % ni "sin política"


def test_cp48_retrying_a_completed_application_creates_no_history(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation], markup="30")
    body = request_body(world)
    submit(client, world, body)
    run_worker(test_engine)
    [row] = applications(test_engine)
    before = prices(test_engine, world)

    with Session(test_engine, expire_on_commit=False) as session:
        service = processing.AutomaticPriceApplicationService(
            AutomaticPricingRepository(session), interval_seconds=1, max_backoff_seconds=1
        )
        assert service.process(UUID(str(row["id"]))) is None  # ya es final: no se procesa otra vez
    again = submit(client, world, body)  # la misma entrega de Purchase es idempotente
    assert [item["id"] for item in again["applications"]] == [str(row["id"])]
    run_worker(test_engine)
    assert prices(test_engine, world) == before
    [same] = applications(test_engine)
    assert same["attempts"] == 1 and same["version"] == row["version"]


def test_cpt09_two_workers_do_not_duplicate(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    presentations = [world.presentation] + [add_presentation(supervisor, company, fake_catalog, world) for _ in range(5)]
    policy(supervisor, world, presentations, markup="30")
    for presentation in presentations:
        submit(client, world, request_body(world, presentation=presentation))
        submit(client, world, request_body(world, presentation=presentation, sequence=2, line_total=SECOND[0],
                                           previous=("23800.00", "10.0000")))

    barrier = threading.Barrier(2)
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            barrier.wait()
            for _ in range(10):
                run_cycle(test_engine, batch_size=50, max_backoff_seconds=300, interval_seconds=0.01)
        except BaseException as error:  # noqa: BLE001
            errors.append(error)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=120)
    run_worker(test_engine)
    assert errors == []

    rows = applications(test_engine)
    assert len(rows) == 12 and {row["status"] for row in rows} == {"APPLIED"}
    assert {row["attempts"] for row in rows} == {1}
    for presentation in presentations:
        history = prices(test_engine, world, presentation=presentation)
        assert [item["unit_price"] for item in history] == [D("3094.00"), D("3900.00")]  # una versión por recepción
        assert current_price(test_engine, world, presentation=presentation) == D("3900.00")


def test_cp06_receipts_of_another_company_never_take_part(supervisor, client, company, other_company, fake_oc, fake_catalog, test_engine) -> None:
    from tests.conftest import user_sub

    fake_oc.add_member(user_sub("supervisor.test"), other_company)
    mine = scenario(supervisor, company, fake_catalog)
    theirs = scenario(supervisor, other_company, fake_catalog)
    policy(supervisor, mine, [mine.presentation], markup="30")
    policy(supervisor, theirs, [theirs.presentation], markup="30")
    submit(client, mine, request_body(mine, sequence=1))
    submit(client, theirs, request_body(theirs, sequence=1, line_total="10000.00"))  # la misma secuencia, otra empresa
    submit(client, mine, request_body(mine, sequence=2, line_total="20000.00", previous=("23800.00", "10.0000")))
    run_worker(test_engine)
    # 2.000 < 2.380 de la recepción anterior de **esta** empresa: promedio 2.190 × 1,30 = 2.847 (el 1.000 ajeno no cuenta)
    assert current_price(test_engine, mine) == D("2847.00")
    assert current_price(test_engine, theirs) == D("1300.00")
    listed = supervisor.get(f"/api/v1/companies/{company}/automatic-price-applications").json()
    assert listed["total_records"] == 2 and {item["company_id"] for item in listed["items"]} == {str(company)}
