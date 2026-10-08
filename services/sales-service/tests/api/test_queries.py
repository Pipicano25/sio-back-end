"""Consultas (Historia 6; FR-027; DS-09; T066)."""

from __future__ import annotations

from datetime import UTC, datetime

from tests.conftest import base, line, sale_body, user_sub


def test_list_with_filters_and_stable_order(seller, as_user, world, clock, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    clock.fixed = datetime(2026, 10, 6, 15, 0, tzinfo=UTC)
    clock.ticking = True
    old = make_draft()  # fecha de negocio 2026-10-06
    clock.fixed = datetime(2026, 10, 7, 15, 0, tzinfo=UTC)
    confirmed = confirm(make_draft()).json()
    newest = make_draft(company_customer_id=world.customer_org)
    admin = as_user("admin.test")
    other_branch = admin.post(f"{base(world)}/sales", json=sale_body(world, branch_id=world.branch_b)).json()

    page = seller.get(f"{base(world)}/sales").json()
    assert page["total_records"] == 4 and page["total_pages"] == 1
    assert [item["id"] for item in page["items"]] == [other_branch["id"], newest["id"], confirmed["id"], old["id"]]
    assert all(item["lines"] is None for item in page["items"])

    def ids(**params):
        return [item["id"] for item in seller.get(f"{base(world)}/sales", params=params).json()["items"]]

    assert ids(status="CONFIRMED") == [confirmed["id"]]
    assert ids(branch_id=str(world.branch_b)) == [other_branch["id"]]
    assert ids(operation_date_to="2026-10-06") == [old["id"]]
    assert ids(operation_date_from="2026-10-07", operation_date_to="2026-10-07") == [
        other_branch["id"], newest["id"], confirmed["id"],
    ]
    assert ids(number=confirmed["number"]) == [confirmed["id"]]
    assert ids(company_customer_id=str(world.customer_org)) == [newest["id"]]
    assert ids(company_customer_id=str(world.customer), page_size=2) == [other_branch["id"], confirmed["id"]]
    assert ids(company_customer_id=str(world.customer), page_size=2, page=2) == [old["id"]]


def test_query_validation(seller, world) -> None:
    assert seller.get(f"{base(world)}/sales", params={"page_size": 101}).status_code == 422
    assert seller.get(f"{base(world)}/sales", params={"status": "OTRO"}).status_code == 422
    response = seller.get(f"{base(world)}/sales", params={"operation_date_from": "2026-10-06", "operation_date_to": "2026-10-01"})
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "INVALID_DATE_RANGE"


def test_get_sale_lines_and_operations(seller, world, make_sequence, make_draft, confirm) -> None:
    make_sequence()
    draft = make_draft(line(world.product), line(world.product_2))
    confirm(draft)
    detail = seller.get(f"{base(world)}/sales/{draft['id']}").json()
    assert len(detail["lines"]) == 2
    lines = seller.get(f"{base(world)}/sales/{draft['id']}/details").json()
    assert [item["line_number"] for item in lines] == [1, 2]
    operations = seller.get(f"{base(world)}/sales/{draft['id']}/operations").json()
    assert [item["operation_type"] for item in operations] == ["CONFIRM"]
    # La operación no expone la clave, el usuario operativo ni el motivo.
    assert not {"idempotency_key", "application_user_id", "reason"} & set(operations[0])


def test_reads_need_membership_but_not_assignment(as_user, world, fakes, make_draft) -> None:
    draft = make_draft()
    fakes.oc.assignments.clear()
    for username in ("reportes.test", "consulta.test", "ventas.test", "supervisor.test"):
        reader = as_user(username)
        assert reader.get(f"{base(world)}/sales").status_code == 200
        assert reader.get(f"{base(world)}/sales/{draft['id']}").status_code == 200
    assert as_user("reportes.test").post(f"{base(world)}/sales", json={}).status_code == 403
    assert as_user("consulta.test").post(f"{base(world)}/sales", json={}).status_code == 403


def test_users_without_read_permission(as_user, world) -> None:
    for username in ("inventario.test", "compras.test"):
        assert as_user(username).get(f"{base(world)}/sales").status_code == 403


def test_membership_is_checked_with_user_token(seller, world, fakes) -> None:
    seller.get(f"{base(world)}/sales")
    authorization, kind, target = fakes.oc.access_calls[-1]
    assert kind == "company" and target == world.company
    from tests.fakes import subject_of

    assert subject_of(authorization) == user_sub("ventas.test")
