"""Integración con servicios reales, **solo** en la pila aislada `sio-it-*` (T132; FR-022-122, FR-022-124).

Antes de la primera solicitud: `SIO_TEST_TARGET=isolated` y `isolation_guard.check_targets` sobre todas las URL,
incluido Keycloak. Si algún destino no es un contenedor aislado, la sesión falla sin enviar nada.
"""

from __future__ import annotations

import pytest

from tests.integration.support import check_isolation, manifest, user_client


@pytest.fixture(scope="session", autouse=True)
def isolated_targets() -> dict[str, str]:
    return check_isolation()


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
