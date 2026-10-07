"""Secuencias de numeración (Historia 5; FR-031, FR-034, P-02; T039)."""

from __future__ import annotations

from uuid import uuid4

from tests.conftest import base, fetch, sequence_body


def url(world, suffix: str = "") -> str:
    return f"{base(world)}/purchase-sequences{suffix}"


def test_create_list_get(buyer, world) -> None:
    created = buyer.post(url(world), json=sequence_body(reset_policy="MONTHLY"))
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["document_kind"] == "PURCHASE" and body["is_active"] is True and body["counters"] == []
    assert buyer.get(url(world)).json()["items"][0]["id"] == body["id"]
    assert buyer.get(url(world, f"/{body['id']}")).json()["prefix"] == "CP"


def test_branch_sequence_must_belong_to_company(buyer, world, fakes) -> None:
    response = buyer.post(url(world), json=sequence_body(branch_id=str(uuid4())))
    assert response.status_code == 422 and response.json()["errors"][0]["code"] == "BRANCH_NOT_FOUND"
    assert buyer.post(url(world), json=sequence_body(branch_id=str(world.branch))).status_code == 201


def test_one_active_per_company_branch_and_kind(buyer, world) -> None:
    first = buyer.post(url(world), json=sequence_body(series_code="A")).json()
    second = buyer.post(url(world), json=sequence_body(series_code="B"))
    assert second.status_code == 409 and second.json()["code"] == "PURCHASE.SEQUENCE_ALREADY_ACTIVE"
    assert buyer.post(url(world), json=sequence_body(series_code="B", branch_id=str(world.branch))).status_code == 201

    deactivated = buyer.post(url(world, f"/{first['id']}/deactivate"), json={"version": first["version"]})
    assert deactivated.status_code == 200 and deactivated.json()["is_active"] is False
    other = buyer.post(url(world), json=sequence_body(series_code="C")).json()
    reactivated = buyer.post(url(world, f"/{first['id']}/reactivate"), json={"version": deactivated.json()["version"]})
    assert reactivated.status_code == 409 and reactivated.json()["code"] == "PURCHASE.SEQUENCE_ALREADY_ACTIVE"
    assert other["is_active"] is True


def test_series_cannot_repeat_in_scope(buyer, world) -> None:
    first = buyer.post(url(world), json=sequence_body(series_code="A")).json()
    buyer.post(url(world, f"/{first['id']}/deactivate"), json={"version": first["version"]})
    response = buyer.post(url(world), json=sequence_body(series_code="A"))
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.SEQUENCE_IN_USE"


def test_format_is_immutable_after_first_number(buyer, world, make_draft, confirm) -> None:
    sequence = buyer.post(url(world), json=sequence_body()).json()
    edited = buyer.put(url(world, f"/{sequence['id']}"), json={**sequence_body(prefix="CQ"), "version": sequence["version"]})
    assert edited.status_code == 200 and edited.json()["prefix"] == "CQ"
    assert confirm(make_draft()).status_code == 200

    current = buyer.get(url(world, f"/{sequence['id']}")).json()
    assert current["counters"] == [{"period_key": "", "current_number": 1, "next_number_preview": "CQ-000002"}]
    for change in ({"prefix": "CP"}, {"separator": "/"}, {"number_length": 8}, {"series_code": "OTRA"},
                   {"reset_policy": "YEARLY"}, {"initial_number": 10}, {"branch_id": str(world.branch)}):
        response = buyer.put(url(world, f"/{sequence['id']}"), json={**sequence_body(prefix="CQ"), **change, "version": current["version"]})
        assert response.status_code == 409, change
        assert response.json()["code"] == "PURCHASE.SEQUENCE_IN_USE"
    maximum = buyer.put(url(world, f"/{sequence['id']}"), json={**sequence_body(prefix="CQ", maximum_number=500), "version": current["version"]})
    assert maximum.status_code == 200 and maximum.json()["maximum_number"] == 500


def test_maximum_cannot_go_below_current(buyer, world, make_draft, confirm) -> None:
    sequence = buyer.post(url(world), json=sequence_body(initial_number=10)).json()
    confirm(make_draft())
    response = buyer.put(url(world, f"/{sequence['id']}"), json={**sequence_body(initial_number=10, maximum_number=10), "version": 1})
    assert response.status_code == 200
    response = buyer.put(url(world, f"/{sequence['id']}"), json={**sequence_body(initial_number=10, maximum_number=10), "version": 1})
    assert response.status_code == 409 and response.json()["code"] == "PURCHASE.VERSION_CONFLICT"


def test_invalid_bodies(buyer, world) -> None:
    for change in ({"prefix": "cp"}, {"separator": "#"}, {"number_length": 0}, {"reset_policy": "WEEKLY"},
                   {"initial_number": 5, "maximum_number": 4}, {"document_kind": "SALE"}, {"is_active": False}):
        assert buyer.post(url(world), json=sequence_body(**change)).status_code == 422, change


def test_permissions_and_membership(as_user, world, fakes) -> None:
    from tests.conftest import user_sub

    assert as_user("reportes.test").post(url(world), json=sequence_body()).status_code == 403
    assert as_user("reportes.test").get(url(world)).status_code == 200
    fakes.oc.members.pop((user_sub("compras.test"), world.company))
    assert as_user("compras.test").get(url(world)).status_code == 404


def test_changes_are_audited(buyer, world, test_engine) -> None:
    created = buyer.post(url(world), json=sequence_body()).json()
    updated = buyer.put(url(world, f"/{created['id']}"), json={**sequence_body(prefix="CX"), "version": 1}).json()
    deactivated = buyer.post(url(world, f"/{created['id']}/deactivate"), json={"version": updated["version"]}).json()
    buyer.post(url(world, f"/{created['id']}/reactivate"), json={"version": deactivated["version"]})
    actions = [row["payload"]["action"] for row in fetch(test_engine, "SELECT payload FROM audit_outbox ORDER BY created_at")]
    assert actions == [
        "CREATE_PURCHASE_SEQUENCE",
        "UPDATE_PURCHASE_SEQUENCE",
        "DEACTIVATE_PURCHASE_SEQUENCE",
        "REACTIVATE_PURCHASE_SEQUENCE",
    ]
