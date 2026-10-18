"""La barrera de aislamiento bloquea un destino no aislado antes de la primera solicitud (T146; SC-022-7, FR-022-124).

Usa destinos que **no** se contactan: la barrera solo lee `docker ps`. Un puerto publicado por un contenedor sin la
etiqueta `sio.integration.isolated=true` (el Keycloak persistente, 8081) o un puerto que no publica nadie hacen
fallar la verificación; nunca se envía una solicitud a esos destinos.
"""

from __future__ import annotations

import socket

import pytest

from tests.integration.support import TARGETS, isolation_guard

pytestmark = pytest.mark.integration


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_persistent_or_unknown_targets_are_rejected() -> None:
    guard = isolation_guard()
    for target in ("http://127.0.0.1:8081/realms/sio/protocol/openid-connect/token",  # contenedor sin etiqueta
                   f"http://127.0.0.1:{free_port()}/api/v1",  # nadie lo publica
                   "https://127.0.0.1:18112/api/v1",  # esquema no verificable
                   "http://10.0.0.5:18112/api/v1"):  # no es de bucle local
        with pytest.raises(guard.IsolationError):
            guard.check_targets({**TARGETS, "otro": target})


def test_missing_authorization_variable_is_rejected() -> None:
    guard = isolation_guard()
    with pytest.raises(guard.IsolationError):
        guard.check_targets(TARGETS, environ={})


def test_isolated_targets_resolve_to_sio_it_containers() -> None:
    resolved = isolation_guard().check_targets(TARGETS)
    assert set(resolved) == set(TARGETS) and all(name.startswith("sio-it-") for name in resolved.values())


def test_docker_operations_only_on_isolated_containers() -> None:
    guard = isolation_guard()
    with pytest.raises(guard.IsolationError):
        guard.check_container("sio-inventory-service")  # persistente: nunca se detiene
    assert guard.check_container("sio-it-inventory-service") == "sio-it-inventory-service"
