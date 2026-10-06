"""Consulta de los eventos de una empresa (US3; FR-030, FR-031, FR-035; T037)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from tests.api.helpers import at, company_events, register


@pytest.fixture
def admin(as_user):
    return as_user("admin.test")


def url(company) -> str:
    return f"/api/v1/companies/{company}/audit-events"


def test_paginated_and_ordered(admin, emitter, company) -> None:
    events = company_events(emitter, company, 25)

    first = admin.get(url(company)).json()
    assert first["page"] == 1 and first["page_size"] == 20
    assert first["total_records"] == 25 and first["total_pages"] == 2
    assert [item["id"] for item in first["items"]] == [event["id"] for event in reversed(events)][:20]

    second = admin.get(url(company), params={"page": 2}).json()
    assert len(second["items"]) == 5

    big = admin.get(url(company), params={"page_size": 100}).json()
    assert len(big["items"]) == 25


def test_ties_are_ordered_by_id_desc(admin, emitter, company) -> None:
    events = [register(emitter, company_id=str(company), occurred_at=at(0)) for _ in range(5)]
    ids = [item["id"] for item in admin.get(url(company)).json()["items"]]
    assert ids == sorted((event["id"] for event in events), reverse=True)


@pytest.mark.parametrize(
    ("param", "matching", "other"),
    [
        ("action", {"action": "INACTIVATE"}, {"action": "CREATE"}),
        ("entity_type", {"entity_type": "PriceList"}, {"entity_type": "CompanySupplier"}),
        ("result", {"result": "FAILURE"}, {"result": "SUCCESS"}),
    ],
)
def test_text_filters(admin, emitter, company, param, matching, other) -> None:
    hit = register(emitter, company_id=str(company), **matching)
    register(emitter, company_id=str(company), **other)

    items = admin.get(url(company), params={param: matching[param]}).json()["items"]
    assert [item["id"] for item in items] == [hit["id"]]


@pytest.mark.parametrize(
    "param",
    ["entity_id", "keycloak_user_id", "application_user_id", "branch_id", "event_id", "correlation_id", "request_id"],
)
def test_uuid_filters(admin, emitter, company, param) -> None:
    value = str(uuid4())
    hit = register(emitter, company_id=str(company), **{param: value} if param != "event_id" else {"event_id": value})
    register(emitter, company_id=str(company))

    items = admin.get(url(company), params={param: value}).json()["items"]
    assert [item["id"] for item in items] == [hit["id"]]


def test_source_service_filter(admin, emitter, as_token, service_token, company) -> None:
    from tests.conftest import CREATE

    other = as_token(service_token(CREATE, client_id="inventory-service"))
    hit = register(other, company_id=str(company))
    register(emitter, company_id=str(company))

    items = admin.get(url(company), params={"source_service": "inventory-service"}).json()["items"]
    assert [item["id"] for item in items] == [hit["id"]]


def test_date_range_and_combined_filters(admin, emitter, company) -> None:
    events = company_events(emitter, company, 10, action="UPDATE")
    register(emitter, company_id=str(company), occurred_at=at(5), action="CREATE")

    items = admin.get(
        url(company),
        params={"occurred_at_from": at(3), "occurred_at_to": at(6), "action": "UPDATE"},
    ).json()["items"]
    assert {item["id"] for item in items} == {event["id"] for event in events[3:7]}


@pytest.mark.parametrize(
    "params",
    [
        {"occurred_at_from": at(5), "occurred_at_to": at(1)},
        {"page_size": 101},
        {"page": 0},
        {"desconocido": "x"},
        {"occurred_at_from": "2026-09-01T12:00:00"},
        {"result": "OK"},
        {"entity_id": "no-uuid"},
    ],
)
def test_invalid_parameters(admin, company, params) -> None:
    response = admin.get(url(company), params=params)
    assert response.status_code == 422
    assert response.json()["code"] == "AUDIT.VALIDATION_ERROR"


def test_get_by_id_and_fields(admin, emitter, company) -> None:
    event = register(
        emitter, company_id=str(company), new_values={"api_key": "x", "name": "n"}, username_snapshot="admin.test"
    )

    response = admin.get(f"{url(company)}/{event['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data == event
    assert data["redacted_paths"] == ["new_values.api_key"]
    assert {"source_service", "created_by", "recorded_at"} <= set(data)
    assert "content_hash" not in data


def test_event_of_other_company_or_unknown_is_404(admin, emitter, company, fake_oc) -> None:
    from tests.conftest import user_sub

    other = uuid4()
    fake_oc.add_member(user_sub("admin.test"), other)
    foreign = register(emitter, company_id=str(other))

    for audit_id in (foreign["id"], str(uuid4())):
        response = admin.get(f"{url(company)}/{audit_id}")
        assert response.status_code == 404
        assert response.json()["code"] == "AUDIT.NOT_FOUND"
