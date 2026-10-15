"""Edición del borrador (FR-004, FR-008; Historia 1 escenario 4; T032)."""

from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import base, count_rows, fetch, line, purchase_body


def url(world, purchase, suffix: str = "") -> str:
    return f"{base(world)}/purchases/{purchase['id']}{suffix}"


def header(world, purchase, **changes):
    body = {
        "branch_id": purchase["branch_id"],
        "company_supplier_id": purchase["company_supplier_id"],
        "operation_date": purchase["operation_date"],
        "payment_method_id": purchase["payment_method_id"],
        "version": purchase["version"],
    }
    body.update({key: str(value) if hasattr(value, "hex") else value for key, value in changes.items()})
    return body


def test_line_changes_bump_version_and_recompute_totals(buyer, world, make_draft) -> None:
    draft = make_draft(line(world.product, "2", "100"))
    added = buyer.post(url(world, draft, "/details"), json={**line(world.product_2, "1", "50"), "version": 1})
    assert added.status_code == 201, added.text
    added = added.json()
    assert added["version"] == 2 and added["total"] == "250.00"
    assert [item["line_number"] for item in added["lines"]] == [1, 2]

    second = added["lines"][1]
    updated = buyer.put(url(world, draft, f"/details/{second['id']}"), json={**line(world.product_2, "3", "50"), "version": 2})
    assert updated.status_code == 200, updated.text
    assert updated.json()["version"] == 3 and updated.json()["total"] == "350.00"

    first = added["lines"][0]
    deleted = buyer.delete(url(world, draft, f"/details/{first['id']}"), params={"version": 3})
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["version"] == 4 and deleted.json()["total"] == "150.00"
    assert [item["line_number"] for item in deleted.json()["lines"]] == [2]  # no se renumera


def test_stale_version_is_409(buyer, world, make_draft, test_engine) -> None:
    draft = make_draft()
    buyer.post(url(world, draft, "/details"), json={**line(world.product_2), "version": 1})
    responses = [
        buyer.post(url(world, draft, "/details"), json={**line(world.product_2), "version": 1}),
        buyer.put(url(world, draft), json=header(world, draft, version=1)),
        buyer.delete(url(world, draft, f"/details/{draft['lines'][0]['id']}"), params={"version": 1}),
    ]
    for response in responses:
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "PURCHASE.VERSION_CONFLICT"
    assert count_rows(test_engine, "purchase_details") == 2


def test_update_header_refreshes_snapshots(buyer, world, make_draft) -> None:
    draft = make_draft()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    response = buyer.put(
        url(world, draft),
        json=header(world, draft, supplier_payment_condition_id=world.condition, operation_date=yesterday, observations="Nota"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["version"] == 2 and body["payment_condition_code_snapshot"] == "CASH"
    assert body["due_date"] == yesterday  # spec 020: solo contado
    assert body["observations"] == "Nota"


def test_changing_branch_requires_both_assignments(buyer, as_user, world, make_draft) -> None:
    draft = make_draft()
    response = buyer.put(url(world, draft), json=header(world, draft, branch_id=world.branch_b))
    assert response.status_code == 403
    assert response.json()["code"] == "PURCHASE.BRANCH_ACCESS_DENIED"
    admin = as_user("admin.test")
    assert admin.put(url(world, draft), json=header(world, draft, branch_id=world.branch_b)).status_code == 200


def test_editing_outside_draft_is_409(buyer, world, make_draft, make_sequence, confirm) -> None:
    make_sequence()
    draft = make_draft()
    confirmed = confirm(draft).json()
    for response in (
        buyer.put(url(world, draft), json=header(world, confirmed)),
        buyer.post(url(world, draft, "/details"), json={**line(world.product), "version": confirmed["version"]}),
        buyer.delete(url(world, draft, f"/details/{draft['lines'][0]['id']}"), params={"version": confirmed["version"]}),
    ):
        assert response.status_code == 409
        assert response.json()["code"] == "PURCHASE.INVALID_STATUS"


def test_unknown_line_is_404(buyer, world, make_draft) -> None:
    from uuid import uuid4

    draft = make_draft()
    response = buyer.put(url(world, draft, f"/details/{uuid4()}"), json={**line(world.product), "version": 1})
    assert response.status_code == 404


def test_dependency_down_changes_nothing(buyer, world, make_draft, fakes, test_engine) -> None:
    draft = make_draft()
    fakes.cr.availability.down = True
    response = buyer.post(url(world, draft, "/details"), json={**line(world.product_2), "version": 1})
    assert response.status_code == 503 and response.json()["dependency"] == "commercial-relationship"
    assert fetch(test_engine, "SELECT version FROM purchases")[0]["version"] == 1


def test_line_edits_are_audited(buyer, world, make_draft, test_engine) -> None:
    draft = make_draft()
    added = buyer.post(url(world, draft, "/details"), json={**line(world.product_2), "version": 1}).json()
    buyer.put(url(world, draft, f"/details/{added['lines'][1]['id']}"), json={**line(world.product_2, "5"), "version": 2})
    buyer.delete(url(world, draft, f"/details/{added['lines'][1]['id']}"), params={"version": 3})
    buyer.put(url(world, draft), json=header(world, draft, version=4))
    actions = [row["payload"]["action"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox ORDER BY created_at")]
    assert actions == [
        "CREATE_PURCHASE",
        "ADD_PURCHASE_DETAIL",
        "UPDATE_PURCHASE_DETAIL",
        "DELETE_PURCHASE_DETAIL",
        "UPDATE_PURCHASE",
    ]


def test_purchase_body_helper(world) -> None:
    assert purchase_body(world)["lines"] == []
