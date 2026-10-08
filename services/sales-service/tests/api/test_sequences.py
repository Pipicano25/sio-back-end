"""Secuencias de numeración (Historia 5; FR-026; T043)."""

from __future__ import annotations

from uuid import uuid4

from tests.conftest import base, fetch, sequence_body


def url(world, suffix: str = "") -> str:
    return f"{base(world)}/sale-sequences{suffix}"


def test_create_list_get(seller, world) -> None:
    created = seller.post(url(world), json=sequence_body(reset_policy="MONTHLY"))
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["document_kind"] == "SALE" and body["is_active"] is True and body["counters"] == []
    assert seller.get(url(world)).json()["items"][0]["id"] == body["id"]
    assert seller.get(url(world, f"/{body['id']}")).json()["prefix"] == "FV"


def test_branch_sequence_must_belong_to_company(seller, world, fakes) -> None:
    response = seller.post(url(world), json=sequence_body(branch_id=str(uuid4())))
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "BRANCH_NOT_FOUND"
    assert seller.post(url(world), json=sequence_body(branch_id=str(world.branch))).status_code == 201


def test_one_active_per_company_branch_and_kind(seller, world) -> None:
    first = seller.post(url(world), json=sequence_body(series_code="A")).json()
    second = seller.post(url(world), json=sequence_body(series_code="B"))
    assert second.status_code == 409 and second.json()["code"] == "SALES.SEQUENCE_ALREADY_ACTIVE"
    assert seller.post(url(world), json=sequence_body(series_code="B", branch_id=str(world.branch))).status_code == 201

    deactivated = seller.post(url(world, f"/{first['id']}/deactivate"), json={"version": first["version"]})
    assert deactivated.status_code == 200 and deactivated.json()["is_active"] is False
    other = seller.post(url(world), json=sequence_body(series_code="C")).json()
    reactivated = seller.post(url(world, f"/{first['id']}/reactivate"), json={"version": deactivated.json()["version"]})
    assert reactivated.status_code == 409 and reactivated.json()["code"] == "SALES.SEQUENCE_ALREADY_ACTIVE"
    assert other["is_active"] is True


def test_series_cannot_repeat_in_scope(seller, world) -> None:
    first = seller.post(url(world), json=sequence_body(series_code="A")).json()
    seller.post(url(world, f"/{first['id']}/deactivate"), json={"version": first["version"]})
    response = seller.post(url(world), json=sequence_body(series_code="A"))
    assert response.status_code == 409 and response.json()["code"] == "SALES.SEQUENCE_IN_USE"


def test_format_is_immutable_after_first_number(seller, world, make_draft, confirm) -> None:
    sequence = seller.post(url(world), json=sequence_body()).json()
    edited = seller.put(url(world, f"/{sequence['id']}"), json={**sequence_body(prefix="CQ"), "version": sequence["version"]})
    assert edited.status_code == 200 and edited.json()["prefix"] == "CQ"
    assert confirm(make_draft()).status_code == 200

    current = seller.get(url(world, f"/{sequence['id']}")).json()
    assert current["counters"] == [{"period_key": "", "current_number": 1, "next_number_preview": "CQ-000002"}]
    for change in ({"prefix": "FV"}, {"separator": "/"}, {"number_length": 8}, {"series_code": "OTRA"},
                   {"reset_policy": "YEARLY"}, {"initial_number": 10}, {"branch_id": str(world.branch)}):
        response = seller.put(url(world, f"/{sequence['id']}"), json={**sequence_body(prefix="CQ"), **change, "version": current["version"]})
        assert response.status_code == 409, change
        assert response.json()["code"] == "SALES.SEQUENCE_IN_USE"
    maximum = seller.put(url(world, f"/{sequence['id']}"), json={**sequence_body(prefix="CQ", maximum_number=500), "version": current["version"]})
    assert maximum.status_code == 200 and maximum.json()["maximum_number"] == 500


def test_maximum_cannot_go_below_current(seller, world, make_draft, confirm) -> None:
    sequence = seller.post(url(world), json=sequence_body(initial_number=10)).json()
    confirm(make_draft())
    response = seller.put(url(world, f"/{sequence['id']}"), json={**sequence_body(initial_number=10, maximum_number=10), "version": 1})
    assert response.status_code == 200
    response = seller.put(url(world, f"/{sequence['id']}"), json={**sequence_body(initial_number=10, maximum_number=10), "version": 1})
    assert response.status_code == 409 and response.json()["code"] == "SALES.VERSION_CONFLICT"


def test_invalid_bodies(seller, world) -> None:
    for change in ({"prefix": "cp"}, {"separator": "#"}, {"number_length": 0}, {"reset_policy": "WEEKLY"},
                   {"initial_number": 5, "maximum_number": 4}, {"document_kind": "SALE"}, {"is_active": False}):
        assert seller.post(url(world), json=sequence_body(**change)).status_code == 422, change


def test_permissions_and_membership(as_user, world, fakes) -> None:
    from tests.conftest import user_sub

    assert as_user("reportes.test").post(url(world), json=sequence_body()).status_code == 403
    assert as_user("reportes.test").get(url(world)).status_code == 200
    fakes.oc.members.pop((user_sub("ventas.test"), world.company))
    assert as_user("ventas.test").get(url(world)).status_code == 404


def test_changes_are_audited(seller, world, test_engine) -> None:
    created = seller.post(url(world), json=sequence_body()).json()
    updated = seller.put(url(world, f"/{created['id']}"), json={**sequence_body(prefix="CX"), "version": 1}).json()
    deactivated = seller.post(url(world, f"/{created['id']}/deactivate"), json={"version": updated["version"]}).json()
    seller.post(url(world, f"/{created['id']}/reactivate"), json={"version": deactivated["version"]})
    actions = [row["payload"]["action"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox ORDER BY created_at")]
    assert actions == [
        "CREATE_SALE_SEQUENCE",
        "UPDATE_SALE_SEQUENCE",
        "DEACTIVATE_SALE_SEQUENCE",
        "REACTIVATE_SALE_SEQUENCE",
    ]
