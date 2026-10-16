"""Consulta y resolución de las actualizaciones automáticas (T053; FR-021-27, FR-021-32a; A2 a A4).

CP-54 (`RESOLVED` libera las siguientes y no se reintenta), `409 APPLICATION_ALREADY_FINAL`, CP-67 (vendedor u otra
empresa no consultan costos), CP-T15 (identidad técnica `403`). Datos ficticios.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from commercial_relationship_service.application.automatic_price_application_service import (
    AutomaticPriceApplicationService,
)
from commercial_relationship_service.audit_context import AuditActor, reset_actor, set_actor
from commercial_relationship_service.infrastructure.pricing_repositories import AutomaticPricingRepository
from tests.api.automatic_pricing_helpers import (
    applications,
    current_price,
    policy,
    request_body,
    run_worker,
    scenario,
    submit,
    technical,
)
from tests.api.helpers import code_of

D = Decimal
URL = "/api/v1/companies/{company}/automatic-price-applications"
REASON = "Recepción revisada manualmente (ficticio)"


@pytest.fixture
def supervisor(as_user):
    return as_user("supervisor.test")


@pytest.fixture
def client(as_token, service_token):
    return technical(as_token, service_token)


def force_failure(test_engine, application_id) -> None:
    """Simula un fallo del worker con una espera larga: la aplicación queda `FAILED` y no se reintenta en la prueba."""
    token = set_actor(AuditActor("system:commercial-relationship-price-worker", "commercial-relationship-price-worker"))
    try:
        with Session(test_engine, expire_on_commit=False) as session:
            service = AutomaticPriceApplicationService(
                AutomaticPricingRepository(session), interval_seconds=3600, max_backoff_seconds=3600
            )
            service.fail(UUID(str(application_id)), RuntimeError("Fallo simulado"))
    finally:
        reset_actor(token)


def _processed_world(supervisor, client, company, fake_catalog, test_engine):
    world = scenario(supervisor, company, fake_catalog)
    created = policy(supervisor, world, [world.presentation], markup="30")
    body = request_body(world)
    submit(client, world, body)
    run_worker(test_engine)
    return world, created, body


def test_a2_a3_list_and_detail_expose_the_trace(supervisor, client, company, fake_catalog, test_engine) -> None:
    world, created, body = _processed_world(supervisor, client, company, fake_catalog, test_engine)
    listed = supervisor.get(URL.format(company=company), params={"purchase_id": body["purchase_id"]})
    assert listed.status_code == 200, listed.text
    [item] = listed.json()["items"]
    assert item["status"] == "APPLIED" and item["purchase_detail_id"] == body["purchase_detail_id"]
    assert item["policy_id"] == created["id"] and item["markup_percentage"] == "30.0000"
    assert item["current_unit_cost"] == "2380" and item["reference_cost"] == "2380" and item["new_price"] == "3094.00"
    assert item["received_by_user_id"] == body["received_by_user_id"] and item["attempts"] == 1

    detail = supervisor.get(f"{URL.format(company=company)}/{item['id']}")
    assert detail.status_code == 200 and detail.json() == item


def test_a2_filters(supervisor, client, company, fake_catalog, test_engine) -> None:
    world, _, _ = _processed_world(supervisor, client, company, fake_catalog, test_engine)
    base = URL.format(company=company)
    assert supervisor.get(base, params={"status": "APPLIED"}).json()["total_records"] == 1
    assert supervisor.get(base, params={"status": "FAILED"}).json()["total_records"] == 0
    assert supervisor.get(base, params={"price_list_id": world.price_list["id"]}).json()["total_records"] == 1
    assert supervisor.get(base, params={"company_product_presentation_id": str(uuid4())}).json()["total_records"] == 0
    assert supervisor.get(base, params={"purchase_id": str(uuid4())}).json()["total_records"] == 0
    assert supervisor.get(base, params={"status": "OTHER"}).status_code == 422


def test_cp54_resolved_frees_the_next_ones_and_is_not_retried(supervisor, client, company, fake_catalog, test_engine, outbox, clear_outbox) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation], markup="30")
    submit(client, world, request_body(world, sequence=1))
    [first] = applications(test_engine)
    force_failure(test_engine, first["id"])
    submit(client, world, request_body(world, sequence=2, line_total="30000.00", previous=("23800.00", "10.0000")))
    run_worker(test_engine)
    assert [row["status"] for row in applications(test_engine)] == ["FAILED", "PENDING"]  # la 2 espera a la 1
    assert current_price(test_engine, world) is None

    current = supervisor.get(f"{URL.format(company=company)}/{first['id']}").json()
    assert current["status"] == "FAILED" and current["last_error_code"] == "RuntimeError"
    clear_outbox()
    resolved = supervisor.post(f"{URL.format(company=company)}/{first['id']}/resolution",
                               json={"version": current["version"], "reason": REASON})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["status"] == "RESOLVED" and resolved.json()["resolution_reason"] == REASON
    assert resolved.json()["resolved_by"] == "sub-supervisor.test" and resolved.json()["new_price_item_id"] is None
    [event] = [event for event in outbox() if event["action"] == "RESOLVE_AUTOMATIC_PRICE"]
    assert event["entity_type"] == "AutomaticPriceApplication" and event["reason"] == REASON

    run_worker(test_engine)
    first_row, second_row = applications(test_engine)
    assert first_row["status"] == "RESOLVED" and first_row["attempts"] == 1  # no se reintenta
    assert second_row["status"] == "APPLIED"
    # 2.380 (anterior) y 3.000 (actual): el actual es mayor, rige 3.000 × 1,30
    assert current_price(test_engine, world) == D("3900.00")


def test_resolving_a_final_application_is_rejected(supervisor, client, company, fake_catalog, test_engine) -> None:
    _processed_world(supervisor, client, company, fake_catalog, test_engine)
    [row] = applications(test_engine)
    current = supervisor.get(f"{URL.format(company=company)}/{row['id']}").json()
    response = supervisor.post(f"{URL.format(company=company)}/{row['id']}/resolution",
                               json={"version": current["version"], "reason": REASON})
    assert response.status_code == 409 and code_of(response) == "APPLICATION_ALREADY_FINAL"


def test_resolution_validates_version_and_reason(supervisor, client, company, fake_catalog, test_engine) -> None:
    world = scenario(supervisor, company, fake_catalog)
    policy(supervisor, world, [world.presentation])
    submit(client, world, request_body(world))
    [row] = applications(test_engine)
    url = f"{URL.format(company=company)}/{row['id']}/resolution"
    assert supervisor.post(url, json={"version": row["version"], "reason": "corto"}).status_code == 422
    assert supervisor.post(url, json={"version": row["version"], "reason": "x" * 501}).status_code == 422
    stale = supervisor.post(url, json={"version": row["version"] + 5, "reason": REASON})
    assert stale.status_code == 409 and code_of(stale) == "VERSION_CONFLICT"
    assert supervisor.post(url, json={"version": row["version"], "reason": REASON}).status_code == 200  # desde PENDING


@pytest.mark.parametrize("username", ["ventas.test", "compras.test", "consulta.test", "reportes.test", "inventario.test"])
def test_cp67_only_admins_and_supervisors(as_user, supervisor, client, company, fake_catalog, test_engine, username) -> None:
    _processed_world(supervisor, client, company, fake_catalog, test_engine)
    [row] = applications(test_engine)
    other = as_user(username)
    base = URL.format(company=company)
    for response in (
        other.get(base),
        other.get(f"{base}/{row['id']}"),
        other.post(f"{base}/{row['id']}/resolution", json={"version": 1, "reason": REASON}),
    ):
        assert response.status_code == 403, (username, response.text)
        assert "automatic_price_applications" not in response.text and "perm:" not in response.text
    assert as_user("admin.test").get(base).status_code == 200


def test_cpt15_technical_identity_is_forbidden(as_token, service_token, supervisor, client, company, fake_catalog, test_engine) -> None:
    _processed_world(supervisor, client, company, fake_catalog, test_engine)
    [row] = applications(test_engine)
    robot = as_token(service_token("perm:all:all:all", client_id="purchase-service"))
    base = URL.format(company=company)
    assert robot.get(base).status_code in (403, 404)
    assert robot.get(f"{base}/{row['id']}").status_code in (403, 404)
    assert robot.post(f"{base}/{row['id']}/resolution", json={"version": 1, "reason": REASON}).status_code in (403, 404)


def test_other_company_is_isolated(supervisor, client, company, other_company, fake_catalog, test_engine) -> None:
    _processed_world(supervisor, client, company, fake_catalog, test_engine)
    [row] = applications(test_engine)
    # la aplicación existe, pero no en la empresa de la ruta ni para quien no es miembro
    assert supervisor.get(f"{URL.format(company=other_company)}/{row['id']}").status_code == 404
    assert supervisor.get(URL.format(company=other_company)).status_code == 404
