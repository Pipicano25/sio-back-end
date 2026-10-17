"""Fixtures de integración real: clientes y datos ficticios creados una vez por sesión."""

from __future__ import annotations

import pytest

from tests.integration.support import (
    SALES,
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
def seller():
    with user_client("ventas.test") as client:
        yield client


@pytest.fixture(scope="session")
def supervisor():
    with user_client("supervisor.test") as client:
        yield client


@pytest.fixture(scope="session")
def operator():
    with service_client("inventory-test-operator", "INVENTORY_TEST_OPERATOR_CLIENT_SECRET") as client:
        yield client


@pytest.fixture(scope="session")
def sales_technical():
    with service_client("sales-service", "SALES_SERVICE_CLIENT_SECRET") as client:
        yield client


@pytest.fixture(scope="session")
def real_world(admin) -> RealWorld:
    return build_world(admin)


@pytest.fixture(scope="session")
def sequence(seller, real_world):
    response = seller.post(
        f"{SALES}/companies/{real_world.company}/sale-sequences",
        json={"series_code": "PRINCIPAL", "prefix": "FV", "separator": "-", "initial_number": 1, "number_length": 6, "reset_policy": "MONTHLY"},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture(scope="session", autouse=True)
def isolated_targets() -> None:
    """Barrera de aislamiento antes de la primera prueba (incidente del 2026-10-16): falla si algún destino no es la
    pila aislada `sio-it-*` (`validation/isolation_guard.py`)."""
    from tests.integration.support import check_isolation

    check_isolation()
