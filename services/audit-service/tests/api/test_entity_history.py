"""Historial de una entidad (US4; FR-032; T046)."""

from __future__ import annotations

from uuid import uuid4

from tests.api.helpers import at, register
from tests.conftest import user_sub


def test_company_history_in_chronological_order(as_user, emitter, company, fake_oc) -> None:
    entity = str(uuid4())
    created = register(emitter, company_id=str(company), entity_id=entity, action="CREATE", occurred_at=at(1))
    failure = register(
        emitter, company_id=str(company), entity_id=entity, action="UPDATE", result="FAILURE", occurred_at=at(3)
    )
    update = register(emitter, company_id=str(company), entity_id=entity, action="UPDATE", occurred_at=at(2))
    change = register(emitter, company_id=str(company), entity_id=entity, action="CHANGE_PRICE", occurred_at=at(4))
    register(emitter, company_id=str(company), occurred_at=at(5))
    register(emitter, company_id=str(company), entity_id=entity, entity_type="PriceList", occurred_at=at(5))

    url = f"/api/v1/companies/{company}/entity-history/PriceListItem/{entity}"
    admin = as_user("admin.test")
    body = admin.get(url).json()

    assert [item["id"] for item in body["items"]] == [created["id"], update["id"], failure["id"], change["id"]]
    assert body["items"][0]["new_values"] == {"unit_price": "2100.00"}

    failures = admin.get(url, params={"result": "FAILURE"}).json()["items"]
    assert [item["id"] for item in failures] == [failure["id"]]

    ranged = admin.get(url, params={"occurred_at_from": at(2), "occurred_at_to": at(3)}).json()["items"]
    assert [item["id"] for item in ranged] == [update["id"], failure["id"]]

    paged = admin.get(url, params={"page_size": 3, "page": 2}).json()
    assert paged["total_records"] == 4 and [item["id"] for item in paged["items"]] == [change["id"]]


def test_empty_or_foreign_entity_returns_empty_page(as_user, emitter, company, fake_oc) -> None:
    other = uuid4()
    fake_oc.add_member(user_sub("admin.test"), other)
    entity = str(uuid4())
    register(emitter, company_id=str(other), entity_id=entity)

    response = as_user("admin.test").get(f"/api/v1/companies/{company}/entity-history/PriceListItem/{entity}")

    assert response.status_code == 200
    assert response.json()["items"] == [] and response.json()["total_records"] == 0


def test_platform_history_is_separate(as_user, emitter, company) -> None:
    entity = str(uuid4())
    platform = register(emitter, company_id=None, entity_type="GlobalProduct", entity_id=entity)
    register(emitter, company_id=str(company), entity_type="GlobalProduct", entity_id=entity)

    admin = as_user("admin.test")
    items = admin.get(f"/api/v1/platform-entity-history/GlobalProduct/{entity}").json()["items"]
    assert [item["id"] for item in items] == [platform["id"]]

    company_items = admin.get(f"/api/v1/companies/{company}/entity-history/GlobalProduct/{entity}").json()["items"]
    assert platform["id"] not in {item["id"] for item in company_items}


def test_invalid_entity_type_in_path(as_user, company) -> None:
    response = as_user("admin.test").get(f"/api/v1/companies/{company}/entity-history/price_list/{uuid4()}")
    assert response.status_code == 422
