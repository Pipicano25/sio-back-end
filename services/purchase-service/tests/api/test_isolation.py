"""Aislamiento por empresa (FR-040; RC-04; SC-006; T062)."""

from __future__ import annotations

from uuid import uuid4

from tests.api.routes import ROUTES
from tests.conftest import base, new_key, user_sub


def concrete(path: str, company, ids: dict) -> str:
    return path.format(company=company, **ids)


def test_non_member_gets_404_everywhere(as_user, world, fakes, make_sequence, make_draft, confirm) -> None:
    sequence = make_sequence()
    draft = make_draft()
    confirm(draft)
    fakes.oc.members.pop((user_sub("compras.test"), world.company))
    client = as_user("compras.test")
    ids = {"purchase": draft["id"], "detail": draft["lines"][0]["id"], "operation": uuid4(), "sequence": sequence["id"]}
    for method, path, _ in ROUTES:
        response = client.request(
            method, concrete(path, world.company, ids), json={"version": 1, "reason": "x"}, headers={"Idempotency-Key": new_key()}
        )
        assert response.status_code in (404, 422), (method, path, response.status_code)
        if response.status_code == 404:
            assert response.json()["code"] == "PURCHASE.NOT_FOUND"


def test_member_of_another_company_never_sees_foreign_data(as_user, world, fakes, make_sequence, make_draft, confirm) -> None:
    sequence = make_sequence()
    draft = make_draft()
    confirmed = confirm(draft).json()
    fakes.oc.add_member(user_sub("reportes.test"), world.other_company)
    fakes.oc.members.pop((user_sub("reportes.test"), world.company))
    reader = as_user("reportes.test")
    other = f"/api/v1/companies/{world.other_company}"
    assert reader.get(f"{other}/purchases").json()["items"] == []
    assert reader.get(f"{other}/purchases/{draft['id']}").status_code == 404
    assert reader.get(f"{other}/purchases/{draft['id']}/details").status_code == 404
    assert reader.get(f"{other}/purchases/{draft['id']}/operations").status_code == 404
    assert reader.get(f"{other}/purchases/{draft['id']}/lifecycle-events").status_code == 404
    operation = as_user("compras.test").get(f"{base(world)}/purchases/{draft['id']}/operations").json()[0]
    assert reader.get(f"{other}/purchase-operations/{operation['id']}").status_code == 404
    assert reader.get(f"{other}/purchase-sequences").json()["items"] == []
    assert reader.get(f"{other}/purchase-sequences/{sequence['id']}").status_code == 404
    assert reader.get(f"{other}/purchases", params={"number": confirmed["number"]}).json()["items"] == []


def test_foreign_id_and_unknown_id_give_identical_404(as_user, world, fakes, make_draft) -> None:
    draft = make_draft()
    fakes.oc.add_member(user_sub("reportes.test"), world.other_company)
    reader = as_user("reportes.test")
    other = f"/api/v1/companies/{world.other_company}"
    foreign = reader.get(f"{other}/purchases/{draft['id']}").json()
    unknown = reader.get(f"{other}/purchases/{uuid4()}").json()
    assert {key: foreign[key] for key in ("code", "detail", "status")} == {key: unknown[key] for key in ("code", "detail", "status")}
