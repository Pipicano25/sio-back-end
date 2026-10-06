"""Fixtures de integración real: clientes y datos ficticios creados una vez por sesión."""

from __future__ import annotations

import pytest

from tests.integration.support import RealWorld, build_world, operator_client, require_inventory, user_client


@pytest.fixture(scope="session")
def admin():
    require_inventory()
    with user_client("admin.test") as client:
        yield client


@pytest.fixture(scope="session")
def operator():
    with operator_client() as client:
        yield client


@pytest.fixture(scope="session")
def real_world(admin) -> RealWorld:
    return build_world(admin)
