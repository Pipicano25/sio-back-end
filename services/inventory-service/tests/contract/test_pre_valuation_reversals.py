"""Reversos de operaciones anteriores a la valoración (FR-053, DS-16, DS-17, RN-04; punto 4; T022).

Se siembran operaciones de la Fase A en un esquema temporal migrado a `0001`, se
aplica `0002` (capas de apertura) y se usa la API real sobre ese esquema.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal as D
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from inventory_service.main import create_app
from tests.conftest import ApiClient, OPERATOR_ROLES, line, run_alembic
from tests.contract.fase_a_seed import FaseASeeder
from tests.contract.test_opening_migration import schema_url

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"
SCHEMA = "pre_valuation"


@dataclasses.dataclass
class Seeded:
    company: object
    branch: object
    user: object
    product_a: object  # entrada 10 a 500 y salida 4 → apertura 6 a 500
    product_b: object  # entrada 3 sin costo y 5 a 200 → apertura 8 a 200
    product_c: object  # entrada 4 sin costo → apertura 4 "sin costo"
    entry_a: tuple
    output_a: tuple
    entry_b_no_cost: tuple
    entry_c: tuple


@pytest.fixture
def scratch_engine(test_database_url):
    admin = create_engine(test_database_url)
    with admin.begin() as connection:
        connection.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
        connection.execute(text(f"CREATE SCHEMA {SCHEMA}"))
    url = schema_url(test_database_url, SCHEMA)
    run_alembic(url, "upgrade", "0001")
    engine = create_engine(url)
    yield url, engine
    engine.dispose()
    with admin.begin() as connection:
        connection.execute(text(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE"))
    admin.dispose()


@pytest.fixture
def seeded(scratch_engine, fake_oc, fake_cr) -> Seeded:
    url, engine = scratch_engine
    company = uuid4()
    branch = fake_oc.add_branch(company)
    user = fake_oc.add_user(company)
    products = [fake_cr.add_product(company) for _ in range(3)]
    with engine.begin() as connection:
        s = FaseASeeder(connection, company, branch, application_user_id=user)
        entry_a = s.entry(products[0], 10, 500)
        output_a = s.output(products[0], 4)
        entry_b = s.entry(products[1], 3)
        s.entry(products[1], 5, 200)
        entry_c = s.entry(products[2], 4)
        s.flush_balances()
    run_alembic(url, "upgrade", "head")
    return Seeded(company, branch, user, *products, entry_a, output_a, entry_b, entry_c)


@pytest.fixture
def client(scratch_engine, seeded, test_settings, test_auth, fake_oc, fake_cr, service_token) -> ApiClient:
    url, _ = scratch_engine
    settings = dataclasses.replace(test_settings, database_url=url)
    app = create_app(
        settings,
        auth=test_auth,
        operational_context_factory=fake_oc.directory,
        commercial_relationship_factory=fake_cr.directory,
        access_directory_factory=fake_oc.access_for,
    )
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield ApiClient(test_client, service_token(*OPERATOR_ROLES))


def body(seeded: Seeded, **overrides) -> dict:
    data = {
        "operation_key": str(uuid4()),
        "company_id": str(seeded.company),
        "application_user_id": str(seeded.user),
        "correlation_id": str(uuid4()),
        "reason": "Anulación del documento ficticio de validación",
    }
    data.update(overrides)
    return data


def state(engine) -> dict:
    with engine.connect() as connection:
        return {
            table: connection.execute(text(f"SELECT * FROM {table} ORDER BY 1")).all()
            for table in (
                "inventory_operations",
                "inventory_movements",
                "inventory_balances",
                "inventory_cost_layers",
                "inventory_cost_consumptions",
            )
        }


def test_fase_a_output_reversal_is_output_not_valued(client, seeded, scratch_engine) -> None:
    _, engine = scratch_engine
    before = state(engine)
    response = client.post(f"{OUTPUTS}/{seeded.output_a[0]}/reversal", json=body(seeded))
    assert response.status_code == 409
    assert response.json()["code"] == "INVENTORY.OUTPUT_NOT_VALUED"
    assert state(engine) == before


def test_fase_a_entry_reversal_needs_enough_opening_quantity(client, seeded, scratch_engine) -> None:
    _, engine = scratch_engine
    before = state(engine)
    # La apertura de A conserva 6 y la entrada original fue de 10.
    response = client.post(f"{ENTRIES}/{seeded.entry_a[0]}/reversal", json=body(seeded))
    assert response.status_code == 409
    assert response.json()["code"] == "INVENTORY.ENTRY_LAYER_CONSUMED"
    assert state(engine) == before


def test_fase_a_entry_reversal_retires_units_from_the_opening_layer(client, seeded, scratch_engine) -> None:
    _, engine = scratch_engine
    response = client.post(f"{ENTRIES}/{seeded.entry_b_no_cost[0]}/reversal", json=body(seeded))
    assert response.status_code == 201, response.text
    movement = response.json()["movements"][0]
    # Se retira de la apertura con su costo (200, conocido), no con el de la entrada original (sin costo).
    assert (movement["unit_cost"], movement["movement_value"], movement["cost_known"]) == ("200.0000", "600.00", True)
    with engine.connect() as connection:
        opening = connection.execute(
            text("SELECT remaining_quantity, status FROM inventory_cost_layers WHERE company_product_id = :p"),
            {"p": seeded.product_b},
        ).one()
        consumption = connection.execute(text("SELECT consumption_type, quantity FROM inventory_cost_consumptions")).one()
    assert tuple(opening) == (D("5"), "OPEN")
    assert tuple(consumption) == ("ENTRY_REVERSAL", D("3"))


def test_fase_a_entry_reversal_from_an_unknown_cost_opening_keeps_the_mark(client, seeded) -> None:
    response = client.post(f"{ENTRIES}/{seeded.entry_c[0]}/reversal", json=body(seeded))
    assert response.status_code == 201, response.text
    movement = response.json()["movements"][0]
    assert (movement["unit_cost"], movement["movement_value"], movement["cost_known"]) == ("0.0000", "0.00", False)
    assert response.json()["balances"][0]["has_unknown_cost"] is False  # la apertura quedó agotada


def test_reversals_do_not_change_the_cost_of_outputs_already_applied(client, seeded, scratch_engine) -> None:
    """RN-04 con datos heredados: una salida posterior a la migración conserva su costo."""
    _, engine = scratch_engine
    product = seeded.product_a

    def operation(origin_type, *lines):
        return {
            "operation_key": str(uuid4()),
            "company_id": str(seeded.company),
            "branch_id": str(seeded.branch),
            "origin_type": origin_type,
            "origin_id": str(uuid4()),
            "application_user_id": str(seeded.user),
            "correlation_id": str(uuid4()),
            "reason": None,
            "lines": list(lines),
        }

    sale = client.post(OUTPUTS, json=operation("SALE", line(product, "4")))
    assert sale.status_code == 201, sale.text
    movement_id = sale.json()["movements"][0]["id"]
    assert sale.json()["movements"][0]["movement_value"] == "2000.00"  # 4 de la apertura a 500

    def history():
        with engine.connect() as connection:
            return (
                connection.execute(
                    text("SELECT unit_cost, movement_value, cost_known FROM inventory_movements WHERE id = :m"), {"m": movement_id}
                ).all(),
                connection.execute(
                    text("SELECT cost_layer_id, quantity, unit_cost, cost_amount FROM inventory_cost_consumptions WHERE movement_id = :m"),
                    {"m": movement_id},
                ).all(),
            )

    before = history()
    assert client.post(f"{OUTPUTS}/{seeded.output_a[0]}/reversal", json=body(seeded)).status_code == 409
    assert client.post(f"{ENTRIES}/{seeded.entry_a[0]}/reversal", json=body(seeded)).status_code == 409
    assert client.post(ENTRIES, json=operation("PURCHASE", line(product, "2", unit_cost="900"))).status_code == 201
    assert client.post(f"{ENTRIES}/{seeded.entry_b_no_cost[0]}/reversal", json=body(seeded)).status_code == 201
    assert history() == before
