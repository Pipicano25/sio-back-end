"""Integración con servicios reales, solo en la pila aislada (spec 023).

La barrera de aislamiento valida todas las URL antes de la primera solicitud; si el servicio todavía no está en la
pila, todas las pruebas se omiten con el motivo.
"""

from __future__ import annotations

import pytest

from tests.integration.support import TARGETS, isolation_guard, manifest, user_client


@pytest.fixture(scope="session", autouse=True)
def isolated_targets() -> dict[str, str]:
    guard = isolation_guard()
    try:
        return guard.check_targets(TARGETS)
    except guard.IsolationError as error:
        if "business_reporting" in str(error) or "18113" in str(error):
            pytest.skip("sio-it-business-reporting-service no está en la pila aislada (agregarlo requiere autorización)")
        raise


@pytest.fixture(scope="session")
def seed() -> dict:
    return manifest()


@pytest.fixture(scope="session")
def users():
    clients = {}

    def get(username: str):
        if username not in clients:
            clients[username] = user_client(username)
        return clients[username]

    yield get
    for client in clients.values():
        client.close()
