"""Compras del período para reportes (spec 023, PUR-R1).

Requieren la base de pruebas de Purchase (`PURCHASE_TEST_DATABASE_URL`). Por la estrategia aprobada de la spec 023
no se crean bases temporales: se ejecutan cuando exista una base de pruebas aislada autorizada.

Cubren: categorías recibidas, pendientes y anuladas (DR-03), anuladas fuera de `effective_total`, pendientes
nunca como recibidas, borradores excluidos, filas sin líneas, totales del período completo (no de la página),
filtro por categoría y sucursal, período máximo, aislamiento entre empresas y permisos.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from tests.conftest import base, line, user_sub

TODAY = date.today()
PERIOD = {"date_from": (TODAY - timedelta(days=1)).isoformat(), "date_to": (TODAY + timedelta(days=1)).isoformat()}


def period(client, world, **params):
    return client.get(f"{base(world)}/purchase-reports/period", params={**PERIOD, **params})


def seed(world, make_sequence, make_draft, confirm, receive, cancel):
    """Recibida 2 × 1000; pendiente 3 × 1000; recibida y anulada 4 × 1000; anulada sin recibir 5 × 1000; borrador."""
    make_sequence()
    received = confirm(make_draft(line(world.product, "2", "1000"))).json()
    assert receive(received).status_code == 200
    assert confirm(make_draft(line(world.product, "3", "1000"))).status_code == 200
    received_then_cancelled = confirm(make_draft(line(world.product, "4", "1000"))).json()
    received_then_cancelled = receive(received_then_cancelled).json()
    assert cancel(received_then_cancelled).status_code == 200
    pending_then_cancelled = confirm(make_draft(line(world.product, "5", "1000"))).json()
    assert cancel(pending_then_cancelled).status_code == 200
    make_draft(line(world.product, "9", "1000"))


def test_categories_and_effective_totals(buyer, world, make_sequence, make_draft, confirm, receive, cancel) -> None:
    seed(world, make_sequence, make_draft, confirm, receive, cancel)
    response = period(buyer, world)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_records"] == 4  # el borrador no aparece
    assert sorted(item["category"] for item in body["items"]) == ["CANCELLED", "CANCELLED", "PENDING_RECEIPT", "RECEIVED"]
    assert all("lines" not in item for item in body["items"])
    [totals] = body["totals"]
    assert totals == {
        "currency_code": "COP",
        "received_count": 1, "received_total": "2000.00",
        "pending_receipt_count": 1, "pending_receipt_total": "3000.00",
        "cancelled_count": 2, "cancelled_total": "9000.00",
        "effective_total": "5000.00",  # recibidas + pendientes; las anuladas no suman
    }
    cancelled_after_receipt = next(i for i in body["items"] if i["category"] == "CANCELLED" and i["received_at"])
    assert cancelled_after_receipt["receipt_status"] == "RECEIVED"  # significado de la spec 020, sin cambios


def test_category_filter_keeps_period_totals(buyer, world, make_sequence, make_draft, confirm, receive, cancel) -> None:
    seed(world, make_sequence, make_draft, confirm, receive, cancel)
    body = period(buyer, world, category="PENDING_RECEIPT").json()
    assert [item["category"] for item in body["items"]] == ["PENDING_RECEIPT"]
    assert body["totals"][0]["effective_total"] == "5000.00"  # los totales siguen siendo del período completo


def test_pagination_and_branch_filter(buyer, world, make_sequence, make_draft, confirm, receive, cancel) -> None:
    seed(world, make_sequence, make_draft, confirm, receive, cancel)
    first = period(buyer, world, page_size=3).json()
    second = period(buyer, world, page_size=3, page=2).json()
    assert (len(first["items"]), len(second["items"]), first["total_pages"]) == (3, 1, 2)
    assert {i["id"] for i in first["items"]}.isdisjoint({i["id"] for i in second["items"]})
    assert period(buyer, world, branch_id=str(uuid4())).json()["items"] == []


def test_validation(buyer, world) -> None:
    assert period(buyer, world, date_from="2025-01-01", date_to="2026-01-02").status_code == 422  # 367 días
    assert period(buyer, world, category="OTRA").status_code == 422
    assert period(buyer, world, page_size=101).status_code == 422
    assert period(buyer, world, desconocido="x").status_code == 422
    assert buyer.get(f"{base(world)}/purchase-reports/period").status_code == 422


def test_other_company_and_permissions(as_user, make_token, as_token, world, fakes, make_sequence, make_draft, confirm,
                                       receive, cancel) -> None:
    seed(world, make_sequence, make_draft, confirm, receive, cancel)
    assert as_user("compras.test").get(f"/api/v1/companies/{world.other_company}/purchase-reports/period",
                                       params=PERIOD).status_code == 404
    fakes.oc.members.pop((user_sub("compras.test"), world.company))
    assert period(as_user("compras.test"), world).status_code == 404
    unrelated = as_token(make_token("perm:sales:all:all", sub="sin-permiso-" + uuid4().hex))
    assert period(unrelated, world).status_code == 403
