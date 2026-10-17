"""Historia 2 de la spec 021 (Purchase): serie de costos por presentación y outbox en la T2 de la recepción (T036).

CP-05 (serie por empresa, varias sucursales), CP-46 (recepciones simultáneas), CP-64 (costo anterior de una recepción
previa a la spec), CP-T01 (sin interbloqueos), CP-T02 (rollback de T2 sin solicitud), CP-T03 (el conciliador también
genera la solicitud), CP-43 y CP-53 (anular no cambia la serie), CP-44 (una compra confirmada no admite editar
costos; T068). Datos ficticios; tasa ficticia del 19 % en el arroz.
"""

from __future__ import annotations

import threading

import pytest

from tests.conftest import base, fetch, line, new_key, purchase_body, user_sub

OUTBOX = "SELECT * FROM purchase_price_update_outbox ORDER BY created_at, sequence"
SERIES = "SELECT * FROM purchase_presentation_cost_series"


def _confirmed(client, world, confirm, *lines, branch=None):
    body = purchase_body(world, *lines, **({"branch_id": str(branch)} if branch else {}))
    draft = client.post(f"{base(world)}/purchases", json=body)
    assert draft.status_code == 201, draft.text
    confirmed = confirm(draft.json(), client=client)
    assert confirmed.status_code == 200, confirmed.text
    return confirmed.json()


def _arroz(world, quantity="2", unit_cost="120000"):
    return line(world.product, quantity, unit_cost, company_product_presentation_id=world.presentation)


def test_first_receipt_writes_sequence_one_with_the_paid_line_total(buyer, world, make_sequence, confirm, receive, test_engine) -> None:
    make_sequence()
    purchase = _confirmed(buyer, world, confirm, _arroz(world))
    received = receive(purchase).json()
    [request] = fetch(test_engine, OUTBOX)
    assert request["status"] == "PENDING" and request["sequence"] == 1
    assert str(request["purchase_detail_id"]) == received["lines"][0]["id"]
    payload = request["payload"]
    assert payload == {
        "contract_version": 1,
        "purchase_detail_id": received["lines"][0]["id"],
        "purchase_id": received["id"],
        "branch_id": str(world.branch),
        "company_product_id": str(world.product),
        "company_product_presentation_id": str(world.presentation),
        "sequence": 1,
        "previous_sequence": None,
        "currency_code": "COP",
        "line_total": "285600.00",  # 240.000 + 19 % de impuesto: el costo real pagado, sin dividir
        "quantity": "2.0000",
        "previous_purchase_detail_id": None,
        "previous_line_total": None,
        "previous_quantity": None,
        "received_at": payload["received_at"],
        "received_by_user_id": received["received_by_user_id"],
    }
    assert payload["received_at"].startswith(received["received_at"][:19])
    [series] = fetch(test_engine, SERIES)
    assert series["last_sequence"] == 1 and str(series["last_line_total"]) == "285600.00"


def test_cp05_series_is_per_company_across_branches(as_user, buyer, world, make_sequence, confirm, receive, test_engine) -> None:
    make_sequence()
    admin = as_user("admin.test")  # miembro de las sucursales A y B
    first = _confirmed(buyer, world, confirm, _arroz(world))
    receive(first)
    make_sequence_b = admin.post(f"{base(world)}/purchase-sequences", json={
        "series_code": "SEDE-B", "prefix": "CB", "separator": "-", "initial_number": 1, "number_length": 6,
        "reset_policy": "NEVER", "branch_id": str(world.branch_b),
    })
    assert make_sequence_b.status_code in (201, 409), make_sequence_b.text
    second = _confirmed(admin, world, confirm, _arroz(world, "2", "110000"), branch=world.branch_b)
    assert receive(second, client=admin).status_code == 200

    first_request, second_request = fetch(test_engine, OUTBOX)
    assert (first_request["sequence"], second_request["sequence"]) == (1, 2)
    payload = second_request["payload"]
    assert payload["branch_id"] == str(world.branch_b) and payload["previous_sequence"] == 1
    assert payload["previous_line_total"] == "285600.00" and payload["previous_quantity"] == "2.0000"
    assert payload["previous_purchase_detail_id"] == first_request["payload"]["purchase_detail_id"]
    assert payload["line_total"] == "261800.00"  # 220.000 + 19 %
    assert len(fetch(test_engine, SERIES)) == 1


def test_each_presentation_has_its_own_series(buyer, world, make_sequence, confirm, receive, test_engine) -> None:
    make_sequence()
    purchase = _confirmed(buyer, world, confirm, _arroz(world), line(world.product_2, "3", "1000"))
    receive(purchase)
    requests = fetch(test_engine, OUTBOX)
    assert sorted(request["sequence"] for request in requests) == [1, 1]
    assert len({request["company_product_presentation_id"] for request in requests}) == 2
    assert len(fetch(test_engine, SERIES)) == 2


def test_cp43_cp53_cancellation_does_not_change_the_series(buyer, world, make_sequence, confirm, receive, test_engine) -> None:
    make_sequence()
    first = receive(_confirmed(buyer, world, confirm, _arroz(world))).json()
    cancelled = buyer.post(
        f"{base(world)}/purchases/{first['id']}/cancellation",
        json={"version": first["version"], "reason": "Error de digitación (ficticio)"},
        headers={"Idempotency-Key": new_key()},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert len(fetch(test_engine, OUTBOX)) == 1  # la anulación no genera solicitudes
    receive(_confirmed(buyer, world, confirm, _arroz(world, "2", "100000")))
    second = fetch(test_engine, OUTBOX)[1]["payload"]
    # M-1: la recepción siguiente se compara con la anulada (la serie no se reescribe).
    assert second["previous_sequence"] == 1 and second["previous_line_total"] == "285600.00"


@pytest.mark.parametrize("received", [False, True])
def test_cp44_a_confirmed_purchase_does_not_accept_cost_changes(buyer, world, make_sequence, confirm, receive, test_engine, received) -> None:
    make_sequence()
    purchase = _confirmed(buyer, world, confirm, _arroz(world))
    if received:
        purchase = receive(purchase).json()
    detail = purchase["lines"][0]
    edit = buyer.put(f"{base(world)}/purchases/{purchase['id']}/details/{detail['id']}",
                     json={**_arroz(world, "2", "90000"), "version": purchase["version"]})
    assert edit.status_code == 409 and edit.json()["code"].endswith("INVALID_STATUS"), edit.text
    added = buyer.post(f"{base(world)}/purchases/{purchase['id']}/details",
                       json={**line(world.product_2, "1", "500"), "version": purchase["version"]})
    assert added.status_code == 409 and added.json()["code"].endswith("INVALID_STATUS")
    [row] = fetch(test_engine, "SELECT unit_cost, total FROM purchase_details")
    assert str(row["unit_cost"]) == "120000.0000" and str(row["total"]) == "285600.00"
    assert len(fetch(test_engine, OUTBOX)) == (1 if received else 0)


def test_cp64_first_receipt_after_deploy_uses_the_previous_received_line(buyer, world, make_sequence, confirm, receive, test_engine) -> None:
    make_sequence()
    receive(_confirmed(buyer, world, confirm, _arroz(world)))
    # Simula una recepción anterior a la spec 021: existe la compra recibida, pero no su serie ni su solicitud.
    with test_engine.begin() as connection:
        from sqlalchemy import text

        for table, trigger in (("purchase_price_update_outbox", "tr_purchase_price_update_outbox_no_delete"),
                               ("purchase_presentation_cost_series", "tr_purchase_presentation_cost_series_no_delete")):
            connection.execute(text(f"ALTER TABLE {table} DISABLE TRIGGER {trigger}"))
            connection.execute(text(f"DELETE FROM {table}"))
            connection.execute(text(f"ALTER TABLE {table} ENABLE TRIGGER {trigger}"))
    receive(_confirmed(buyer, world, confirm, _arroz(world, "2", "100000")))
    [request] = fetch(test_engine, OUTBOX)
    payload = request["payload"]
    assert request["sequence"] == 1 and payload["previous_sequence"] is None
    assert payload["previous_line_total"] == "285600.00" and payload["previous_quantity"] == "2.0000"


def _receive_in_threads(test_client, user_token, world, purchases, username="admin.test"):
    barrier = threading.Barrier(len(purchases))
    statuses = []
    lock = threading.Lock()

    def attempt(purchase) -> None:
        barrier.wait(5)
        response = test_client.post(
            f"{base(world)}/purchases/{purchase['id']}/receipt",
            json={"version": purchase["version"], "full_receipt_confirmed": True},
            headers={"Authorization": f"Bearer {user_token(username)}", "Idempotency-Key": new_key()},
        )
        with lock:
            statuses.append(response.status_code)

    threads = [threading.Thread(target=attempt, args=(purchase,)) for purchase in purchases]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(60)
    return statuses


def test_cp46_simultaneous_receipts_get_consecutive_sequences(test_client, user_token, as_user, world, fakes, make_sequence, confirm, test_engine) -> None:
    make_sequence()
    admin = as_user("admin.test")
    purchases = [_confirmed(admin, world, confirm, _arroz(world, "1", str(1000 + index))) for index in range(4)]
    fakes.inventory.availability.latency = 0.05
    assert _receive_in_threads(test_client, user_token, world, purchases) == [200] * 4
    requests = fetch(test_engine, OUTBOX)
    assert sorted(request["sequence"] for request in requests) == [1, 2, 3, 4]
    by_sequence = {request["sequence"]: request["payload"] for request in requests}
    for sequence in (2, 3, 4):  # cada una se compara con el costo real de la anterior de la serie
        assert by_sequence[sequence]["previous_line_total"] == by_sequence[sequence - 1]["line_total"]


def test_cpt01_crossed_presentations_do_not_deadlock(test_client, user_token, as_user, world, fakes, make_sequence, confirm, test_engine) -> None:
    make_sequence()
    admin = as_user("admin.test")
    first = _confirmed(admin, world, confirm, _arroz(world), line(world.product_2, "1", "1000"))
    second = _confirmed(admin, world, confirm, line(world.product_2, "2", "1000"), _arroz(world, "1", "1000"))
    assert _receive_in_threads(test_client, user_token, world, [first, second]) == [200, 200]
    assert len(fetch(test_engine, OUTBOX)) == 4


def test_cpt02_a_failure_in_t2_leaves_neither_series_nor_request(buyer, world, make_sequence, confirm, receive, test_engine, monkeypatch) -> None:
    from purchase_service.application import operation_engine

    make_sequence()
    purchase = _confirmed(buyer, world, confirm, _arroz(world))

    def broken(*args, **kwargs):
        raise RuntimeError("fallo simulado después de escribir la serie")

    monkeypatch.setattr(operation_engine.audit, "record", broken)
    response = receive(purchase)
    assert response.status_code >= 500
    assert fetch(test_engine, OUTBOX) == [] and fetch(test_engine, SERIES) == []
    assert fetch(test_engine, "SELECT received_at FROM purchases")[0]["received_at"] is None


def test_cpt03_the_reconciler_also_writes_the_request(world, fakes, make_sequence, make_draft, confirm, receive, test_engine) -> None:
    from tests.contract.reconciler_support import age_pending, run_reconciler

    make_sequence()
    confirmed = confirm(make_draft(_arroz(world))).json()
    fakes.inventory.lose_response = 1  # Inventory aplica y la respuesta se pierde
    assert receive(confirmed).status_code == 503
    assert fetch(test_engine, OUTBOX) == []
    age_pending(test_engine)
    result = run_reconciler(test_engine, fakes.inventory)
    assert len(result.completed) == 1
    [request] = fetch(test_engine, OUTBOX)
    assert request["sequence"] == 1 and request["created_by"] == "system:purchase-reconciler"


def test_confirmation_alone_never_requests_prices_the_receipt_does(buyer, world, make_sequence, confirm, receive, test_engine) -> None:
    """Decisión aprobada 1 (FR-021-14): solo la recepción física dispara la actualización; confirmar no escribe nada."""
    make_sequence()
    purchase = _confirmed(buyer, world, confirm, _arroz(world))
    assert purchase["status"] == "CONFIRMED" and purchase["receipt_status"] == "PENDING"
    assert fetch(test_engine, OUTBOX) == [] and fetch(test_engine, SERIES) == []
    received = receive(purchase)
    assert received.status_code == 200, received.text
    assert len(fetch(test_engine, OUTBOX)) == 1 and len(fetch(test_engine, SERIES)) == 1
