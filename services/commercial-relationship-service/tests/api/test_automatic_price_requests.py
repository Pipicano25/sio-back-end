"""Historia 2 de la spec 021 (CR): entrada técnica de solicitudes (T037; FR-021-19, FR-021-20; DS-05, DS-06).

CP-36 (idempotencia), CP-55 y CP-T15 (solo la identidad técnica con `submit`), CP-T06 (`REQUEST_CONFLICT`), CP-T07
(`SEQUENCE_CONFLICT`), CP-07 y CP-08 (expansión por lista con la captura de la política en `received_at`), CP-26
(sin políticas no hay aplicaciones). Datos ficticios.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tests.api.automatic_pricing_helpers import (
    REQUESTS,
    add_presentation,
    SUBMIT,
    applications,
    policy,
    request_body,
    scenario,
    submit,
    technical,
)
from tests.api.helpers import code_of, create_price_list


@pytest.fixture
def supervisor(as_user):
    return as_user("supervisor.test")


def test_a1_accepts_the_request_and_expands_per_list_in_policy_mode(supervisor, as_token, service_token, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    wholesale = create_price_list(supervisor, company, code="MAY")
    manual = create_price_list(supervisor, company, code="MANUAL")  # sin políticas: no recibe aplicaciones (CP-60)
    food = policy(supervisor, world, [world.presentation], markup="30")
    policy(supervisor, world, [world.presentation], markup="20", price_list=wholesale)

    body = request_body(world)
    accepted = submit(technical(as_token, service_token), world, body)
    assert accepted["request_id"]
    by_list = {item["price_list_id"]: item for item in accepted["applications"]}
    assert set(by_list) == {world.price_list["id"], wholesale["id"]} and manual["id"] not in by_list
    assert all(item["status"] == "PENDING" for item in accepted["applications"])

    rows = {str(row["price_list_id"]): row for row in applications(test_engine)}
    assert str(rows[world.price_list["id"]]["policy_id"]) == food["id"]
    assert str(rows[world.price_list["id"]]["markup_percentage"]) == "30.0000"  # CP-08: captura en received_at
    assert str(rows[wholesale["id"]]["markup_percentage"]) == "20.0000"  # CP-07: cada lista con su política


def test_presentation_without_policy_in_a_policy_list_is_captured_without_policy(supervisor, as_token, service_token, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    other = add_presentation(supervisor, company, fake_catalog, world)
    policy(supervisor, world, [other])  # la lista usa políticas, pero no para esta presentación
    submit(technical(as_token, service_token), world, request_body(world))
    [row] = applications(test_engine)
    assert row["policy_id"] is None and row["markup_percentage"] is None and row["status"] == "PENDING"


def test_cp26_company_without_policies_gets_no_applications(supervisor, as_token, service_token, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    accepted = submit(technical(as_token, service_token), world, request_body(world))
    assert accepted["applications"] == [] and applications(test_engine) == []


def test_capture_uses_the_policy_in_force_at_received_at(supervisor, as_token, service_token, company, fake_catalog, test_engine) -> None:
    """RC-021-5: la recepción usa el porcentaje vigente cuando se recibió, aunque cambie antes de llegar a CR."""
    world = scenario(supervisor, company, fake_catalog)
    before_policy = datetime.now(UTC)
    created = policy(supervisor, world, [world.presentation], markup="20")
    received_at = datetime.now(UTC)
    changed = supervisor.post(f"/api/v1/pricing-policies/{created['id']}/percentage", json={"version": 1, "markup_percentage": "30"})
    assert changed.status_code == 200
    client = technical(as_token, service_token)

    submit(client, world, request_body(world, sequence=1, received_at=received_at))
    [row] = applications(test_engine)
    assert str(row["markup_percentage"]) == "20.0000"

    # Una recepción anterior a la primera política no tiene aplicación: la lista aún no estaba en modo políticas.
    early = submit(client, world, request_body(world, sequence=2, received_at=before_policy - timedelta(seconds=1)))
    assert early["applications"] == []


def test_cp36_cpt06_idempotency_by_purchase_detail(supervisor, as_token, service_token, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation])
    client = technical(as_token, service_token)
    body = request_body(world)
    first = submit(client, world, body)
    again = submit(client, world, body)
    assert again == first and len(applications(test_engine)) == 1

    changed = {**body, "line_total": "99999.00"}
    response = client.post(REQUESTS.format(company=company), json=changed)
    assert response.status_code == 409 and code_of(response) == "REQUEST_CONFLICT"


def test_cpt07_sequence_already_used_by_another_line(supervisor, as_token, service_token, company, fake_catalog) -> None:
    world = scenario(supervisor, company, fake_catalog)
    client = technical(as_token, service_token)
    submit(client, world, request_body(world, sequence=1))
    response = client.post(REQUESTS.format(company=company), json=request_body(world, sequence=1))
    assert response.status_code == 409 and code_of(response) == "SEQUENCE_CONFLICT"


def test_presentation_of_another_company_or_product_is_rejected(supervisor, as_token, service_token, company, fake_catalog) -> None:
    world = scenario(supervisor, company, fake_catalog)
    other = scenario(supervisor, company, fake_catalog)
    client = technical(as_token, service_token)
    response = client.post(REQUESTS.format(company=company), json=request_body(world, presentation=other.presentation))
    assert response.status_code == 422 and code_of(response) == "PRESENTATION_NOT_FOUND"


@pytest.mark.parametrize(
    "overrides",
    [
        {"contract_version": 2},
        {"sequence": 0},
        {"sequence": 3, "previous_sequence": 1},
        {"quantity": "0"},
        {"previous_line_total": "100.00", "previous_quantity": None},
        {"currency_code": "pesos"},
        {"line_total": "-1"},
    ],
)
def test_invalid_contract_is_rejected(supervisor, as_token, service_token, company, fake_catalog, overrides) -> None:
    world = scenario(supervisor, company, fake_catalog)
    response = technical(as_token, service_token).post(REQUESTS.format(company=company), json=request_body(world, **overrides))
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("username", ["admin.test", "supervisor.test", "compras.test", "ventas.test"])
def test_cp55_humans_cannot_submit_even_with_the_permission(as_user, company, fake_catalog, username) -> None:
    """La ruta exige identidad técnica además del permiso (`admin.test` lo tiene por `perm:all:all:all`)."""
    supervisor = as_user("supervisor.test")
    world = scenario(supervisor, company, fake_catalog)
    response = as_user(username).post(REQUESTS.format(company=company), json=request_body(world))
    assert response.status_code == 403, response.text


def test_cpt15_technical_identity_without_submit_is_forbidden(supervisor, as_token, service_token, company, fake_catalog) -> None:
    world = scenario(supervisor, company, fake_catalog)
    client = as_token(service_token("perm:commercial-relationship:platform:lookup", client_id="purchase-service"))
    response = client.post(REQUESTS.format(company=company), json=request_body(world))
    assert response.status_code == 403


def test_cpt15_technical_submit_does_not_open_other_writes(supervisor, as_token, service_token, company, fake_catalog) -> None:
    world = scenario(supervisor, company, fake_catalog)
    client = as_token(service_token(SUBMIT, "perm:all:all:all", client_id="purchase-service"))
    response = client.post(f"/api/v1/companies/{company}/price-lists", json={"code": "X", "name": "X", "currency_code": "COP"})
    assert response.status_code in (403, 404)
    response = client.post(
        f"/api/v1/companies/{company}/price-lists/{world.price_list['id']}/pricing-policies",
        json={"name": "X", "markup_percentage": "1", "company_product_presentation_ids": []},
    )
    assert response.status_code in (403, 404)


def test_request_is_audited_with_the_technical_identity(supervisor, as_token, service_token, company, fake_catalog, outbox, clear_outbox) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation])
    clear_outbox()
    body = request_body(world)
    submit(technical(as_token, service_token), world, body)
    [event] = [event for event in outbox() if event["action"] == "RECEIVE_AUTOMATIC_PRICE_REQUEST"]
    assert event["entity_type"] == "AutomaticPriceUpdateRequest"
    assert event["new_values"]["purchase_detail_id"] == body["purchase_detail_id"]
    assert event["new_values"]["received_by_user_id"] == body["received_by_user_id"]  # usuario de negocio
    assert event["username_snapshot"] == "service-account-purchase-service"  # identidad técnica que entregó
