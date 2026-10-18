"""Rendimiento **solo** en la pila aislada (RNF-022-7): la misma barrera que la integración."""

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
