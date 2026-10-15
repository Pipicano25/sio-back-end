"""Consultas (Historia 6; FR-039; DS-09; T061)."""

from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import base, line, user_sub


def test_list_with_filters_and_stable_order(buyer, as_user, world, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    old = make_draft(operation_date=yesterday)
    confirmed = confirm(make_draft()).json()
    newest = make_draft()
    admin = as_user("admin.test")
    other_branch = admin.post(
        f"{base(world)}/purchases",
        json={
            "branch_id": str(world.branch_b),
            "company_supplier_id": str(world.supplier),
            "operation_date": date.today().isoformat(),
            "payment_method_id": str(world.payment_method),
        },
    ).json()

    page = buyer.get(f"{base(world)}/purchases").json()
    assert page["total_records"] == 4 and page["total_pages"] == 1
    assert [item["id"] for item in page["items"]] == [other_branch["id"], newest["id"], confirmed["id"], old["id"]]
    assert all(item["lines"] is None for item in page["items"])

    def ids(**params):
        return [item["id"] for item in buyer.get(f"{base(world)}/purchases", params=params).json()["items"]]

    assert ids(status="CONFIRMED") == [confirmed["id"]]
    assert ids(branch_id=str(world.branch_b)) == [other_branch["id"]]
    assert ids(operation_date_to=yesterday) == [old["id"]]
    assert ids(number=confirmed["number"]) == [confirmed["id"]]
    assert ids(company_supplier_id=str(world.supplier), page_size=2) == [other_branch["id"], newest["id"]]
    assert ids(company_supplier_id=str(world.supplier), page_size=2, page=2) == [confirmed["id"], old["id"]]


def test_query_validation(buyer, world) -> None:
    assert buyer.get(f"{base(world)}/purchases", params={"page_size": 101}).status_code == 422
    assert buyer.get(f"{base(world)}/purchases", params={"status": "OTRO"}).status_code == 422
    response = buyer.get(f"{base(world)}/purchases", params={"operation_date_from": "2026-10-06", "operation_date_to": "2026-10-01"})
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "INVALID_DATE_RANGE"


def test_get_purchase_lines_and_operations(buyer, world, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft(line(world.product), line(world.product_2))
    confirm(draft)
    detail = buyer.get(f"{base(world)}/purchases/{draft['id']}").json()
    assert len(detail["lines"]) == 2
    lines = buyer.get(f"{base(world)}/purchases/{draft['id']}/details").json()
    assert [item["line_number"] for item in lines] == [1, 2]
    operations = buyer.get(f"{base(world)}/purchases/{draft['id']}/operations").json()
    assert [item["operation_type"] for item in operations] == ["CONFIRM"]


def test_reads_need_membership_but_not_assignment(as_user, world, fakes, make_draft) -> None:
    draft = make_draft()
    fakes.oc.assignments.clear()
    for username in ("reportes.test", "consulta.test", "compras.test"):
        reader = as_user(username)
        assert reader.get(f"{base(world)}/purchases").status_code == 200
        assert reader.get(f"{base(world)}/purchases/{draft['id']}").status_code == 200
    assert as_user("reportes.test").post(f"{base(world)}/purchases", json={}).status_code == 403


def test_users_without_read_permission(as_user, world) -> None:
    for username in ("inventario.test", "ventas.test"):
        assert as_user(username).get(f"{base(world)}/purchases").status_code == 403


def test_membership_is_checked_with_user_token(buyer, world, fakes) -> None:
    buyer.get(f"{base(world)}/purchases")
    authorization, kind, target = fakes.oc.access_calls[-1]
    assert kind == "company" and target == world.company
    from tests.fakes import subject_of

    assert subject_of(authorization) == user_sub("compras.test")
