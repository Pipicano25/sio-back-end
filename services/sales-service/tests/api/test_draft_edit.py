"""Edición del borrador (FR-004, FR-006, FR-008, R-12; Historia 1 escenario 5; T035)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from tests.conftest import base, count_rows, fetch, line, sale_body


def url(world, sale, suffix: str = "") -> str:
    return f"{base(world)}/sales/{sale['id']}{suffix}"


def header(world, sale, **changes):
    body = {
        "branch_id": sale["branch_id"],
        "company_customer_id": sale["company_customer_id"],
        "payment_method_id": sale["payment_method_id"],
        "version": sale["version"],
    }
    body.update({key: str(value) if hasattr(value, "hex") else value for key, value in changes.items()})
    return body


def test_line_changes_bump_version_and_recompute_totals(seller, world, make_draft) -> None:
    draft = make_draft(line(world.product, "2"))  # 2 × 1500
    added = seller.post(url(world, draft, "/details"), json={**line(world.product_2, "1"), "version": 1})  # 9000
    assert added.status_code == 201, added.text
    added = added.json()
    assert added["version"] == 2 and added["total"] == "12000.00"
    assert [item["line_number"] for item in added["lines"]] == [1, 2]

    second = added["lines"][1]
    updated = seller.put(url(world, draft, f"/details/{second['id']}"), json={**line(world.product_2, "3"), "version": 2})
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 3 and updated.json()["total"] == "30000.00"

    first = added["lines"][0]
    deleted = seller.delete(url(world, draft, f"/details/{first['id']}"), params={"version": 3})
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["version"] == 4 and deleted.json()["total"] == "27000.00"
    assert [item["line_number"] for item in deleted.json()["lines"]] == [2]  # no se renumera


def test_editing_a_line_resolves_its_price_again(seller, world, make_draft, fakes) -> None:
    """La forma de actualizar una línea tras `PRICES_CHANGED` (FR-006, DS-05)."""
    draft = make_draft(line(world.product, "2"))
    fakes.cr.set_unit_price(world.product, "1600.00")
    detail = draft["lines"][0]
    updated = seller.put(url(world, draft, f"/details/{detail['id']}"), json={**line(world.product, "2"), "version": 1})
    assert updated.status_code == 200, updated.text
    assert updated.json()["lines"][0]["unit_price"] == "1600.0000" and updated.json()["total"] == "3200.00"


def test_stale_version_is_409(seller, world, make_draft, test_engine) -> None:
    draft = make_draft()
    seller.post(url(world, draft, "/details"), json={**line(world.product_2), "version": 1})
    responses = [
        seller.post(url(world, draft, "/details"), json={**line(world.product_2), "version": 1}),
        seller.put(url(world, draft), json=header(world, draft, version=1)),
        seller.delete(url(world, draft, f"/details/{draft['lines'][0]['id']}"), params={"version": 1}),
    ]
    for response in responses:
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "SALES.VERSION_CONFLICT"
    assert count_rows(test_engine, "sale_details") == 2


def test_update_header_refreshes_the_customer(seller, world, make_draft) -> None:
    draft = make_draft()
    response = seller.put(url(world, draft), json=header(world, draft, company_customer_id=world.customer_org, observations="Nota"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == 2 and body["customer_identification_snapshot"] == "NIT 900123456"
    assert body["observations"] == "Nota"
    assert body["operation_date"] == draft["operation_date"]  # misma sucursal: la fecha informativa no cambia


def test_changing_branch_requires_both_assignments_and_recomputes_the_date(as_user, seller, world, make_draft, fakes, clock) -> None:
    clock.fixed = datetime(2026, 10, 8, 2, 0, tzinfo=UTC)  # 21:00 del 7 en Bogotá; el 8 en Madrid
    draft = make_draft()
    assert draft["operation_date"] == "2026-10-07"
    response = seller.put(url(world, draft), json=header(world, draft, branch_id=world.branch_b))
    assert response.status_code == 403
    assert response.json()["code"] == "SALES.BRANCH_ACCESS_DENIED"
    fakes.oc.branches[world.branch_b] = fakes.oc.branches[world.branch_b].__class__(
        world.branch_b, world.company, "ACTIVE", "Europe/Madrid"
    )
    moved = as_user("admin.test").put(url(world, draft), json=header(world, draft, branch_id=world.branch_b))
    assert moved.status_code == 200, moved.text
    assert moved.json()["operation_date"] == "2026-10-08" and moved.json()["due_date"] == "2026-10-08"


def test_editing_outside_draft_is_409(seller, world, make_draft, make_sequence, confirm) -> None:
    make_sequence()
    draft = make_draft()
    confirmed = confirm(draft).json()
    for response in (
        seller.put(url(world, draft), json=header(world, confirmed)),
        seller.post(url(world, draft, "/details"), json={**line(world.product), "version": confirmed["version"]}),
        seller.delete(url(world, draft, f"/details/{draft['lines'][0]['id']}"), params={"version": confirmed["version"]}),
    ):
        assert response.status_code == 409
        assert response.json()["code"] == "SALES.INVALID_STATUS"


def test_unknown_line_is_404(seller, world, make_draft) -> None:
    draft = make_draft()
    response = seller.put(url(world, draft, f"/details/{uuid4()}"), json={**line(world.product), "version": 1})
    assert response.status_code == 404


def test_dependency_down_changes_nothing(seller, world, make_draft, fakes, test_engine) -> None:
    draft = make_draft()
    fakes.cr.availability.down = True
    response = seller.post(url(world, draft, "/details"), json={**line(world.product_2), "version": 1})
    assert response.status_code == 503 and response.json()["dependency"] == "commercial-relationship"
    assert fetch(test_engine, "SELECT version FROM sales")[0]["version"] == 1


def test_line_edits_are_audited_without_costs(seller, world, make_draft, test_engine) -> None:
    draft = make_draft()
    added = seller.post(url(world, draft, "/details"), json={**line(world.product_2), "version": 1}).json()
    seller.put(url(world, draft, f"/details/{added['lines'][1]['id']}"), json={**line(world.product_2, "5"), "version": 2})
    seller.delete(url(world, draft, f"/details/{added['lines'][1]['id']}"), params={"version": 3})
    seller.put(url(world, draft), json=header(world, draft, version=4))
    rows = fetch(test_engine, "SELECT payload FROM audit_outbox ORDER BY created_at")
    assert [row["payload"]["action"] for row in rows] == [
        "CREATE_SALE",
        "ADD_SALE_DETAIL",
        "UPDATE_SALE_DETAIL",
        "DELETE_SALE_DETAIL",
        "UPDATE_SALE",
    ]
    assert not any("cost" in str(row["payload"]) or "margin" in str(row["payload"]) for row in rows)


def test_sale_body_helper(world) -> None:
    assert sale_body(world)["lines"] == []
