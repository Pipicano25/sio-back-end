"""Fixtures de integración real: clientes y datos ficticios creados una vez por sesión."""

from __future__ import annotations

import pytest

from tests.integration.support import (
    PURCHASE,
    RealWorld,
    build_world,
    require_services,
    service_client,
    user_client,
)


@pytest.fixture(scope="session")
def admin():
    require_services()
    with user_client("admin.test") as client:
        yield client


@pytest.fixture(scope="session")
def buyer():
    with user_client("compras.test") as client:
        yield client


@pytest.fixture(scope="session")
def operator():
    with service_client("inventory-test-operator", "INVENTORY_TEST_OPERATOR_CLIENT_SECRET") as client:
        yield client


@pytest.fixture(scope="session")
def purchase_technical():
    with service_client("purchase-service", "PURCHASE_SERVICE_CLIENT_SECRET") as client:
        yield client


@pytest.fixture(scope="session")
def real_world(admin) -> RealWorld:
    return build_world(admin)


@pytest.fixture(scope="session")
def sequence(buyer, real_world):
    response = buyer.post(
        f"{PURCHASE}/companies/{real_world.company}/purchase-sequences",
        json={"series_code": "PRINCIPAL", "prefix": "CP", "separator": "-", "initial_number": 1, "number_length": 6, "reset_policy": "MONTHLY"},
    )
    assert response.status_code == 201, response.text
    return response.json()
