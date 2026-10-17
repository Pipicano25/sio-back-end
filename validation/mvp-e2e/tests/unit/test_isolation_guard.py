"""Barrera de aislamiento (`validation/isolation_guard.py`) con Docker simulado: no toca contenedores ni servicios."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

GUARD_PATH = Path(__file__).resolve().parents[3] / "isolation_guard.py"
spec = importlib.util.spec_from_file_location("isolation_guard_unit", GUARD_PATH)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

ISOLATED = {"SIO_TEST_TARGET": "isolated", "SIO_INTEGRATION_CONTAINER_PREFIX": "sio-it-"}


def docker(*rows: tuple[str, str, bool], labels: dict[str, str] | None = None):
    """Doble de `docker ps --format json` y `docker inspect`."""
    def run(args: list[str]) -> str:
        if args[0] == "ps":
            return "\n".join(json.dumps({"Names": name, "Ports": ports,
                                         "Labels": "sio.integration.isolated=true,otra=x" if isolated else "otra=x"})
                             for name, ports, isolated in rows)
        if args[0] == "inspect":
            return (labels or {}).get(args[-1], "") + "\n"
        raise AssertionError(args)
    return run


PERSISTENT = ("sio-purchase-service", "127.0.0.1:8107->8000/tcp", False)
ISOLATED_PU = ("sio-it-purchase-service", "127.0.0.1:18107->8000/tcp", True)
ISOLATED_KC = ("sio-it-keycloak", "127.0.0.1:18081->8080/tcp", True)


def test_isolated_targets_are_accepted() -> None:
    resolved = guard.check_targets(
        {"purchase": "http://127.0.0.1:18107/api/v1", "keycloak": "http://localhost:18081/realms/sio/protocol/openid-connect/token"},
        environ=ISOLATED, runner=docker(PERSISTENT, ISOLATED_PU, ISOLATED_KC),
    )
    assert resolved == {"keycloak": "sio-it-keycloak", "purchase": "sio-it-purchase-service"}


def test_without_explicit_authorization_nothing_runs() -> None:
    with pytest.raises(guard.IsolationError, match="SIO_TEST_TARGET=isolated"):
        guard.check_targets({"purchase": "http://127.0.0.1:18107"}, environ={}, runner=docker(ISOLATED_PU))


def test_persistent_service_on_localhost_is_rejected() -> None:
    """`localhost` no basta: el puerto 8107 es del contenedor persistente."""
    with pytest.raises(guard.IsolationError, match="sio-purchase-service, que no es un contenedor aislado"):
        guard.check_targets({"purchase": "http://127.0.0.1:8107/api/v1"}, environ=ISOLATED,
                            runner=docker(PERSISTENT, ISOLATED_PU))


@pytest.mark.parametrize("url", ["http://127.0.0.1:19999", "https://127.0.0.1:18107", "http://10.0.0.5:18107",
                                 "http://servicio.ejemplo:18107", "http://127.0.0.1"])
def test_unverifiable_targets_are_rejected(url) -> None:
    with pytest.raises(guard.IsolationError):
        guard.check_targets({"purchase": url}, environ=ISOLATED, runner=docker(ISOLATED_PU))


def test_a_single_unauthorized_target_blocks_everything() -> None:
    with pytest.raises(guard.IsolationError) as error:
        guard.check_targets({"purchase": "http://127.0.0.1:18107", "sales": "http://127.0.0.1:8108"}, environ=ISOLATED,
                            runner=docker(ISOLATED_PU, ("sio-sales-service", "127.0.0.1:8108->8000/tcp", False)))
    assert "sales" in str(error.value) and "purchase" not in str(error.value).split("\n", 1)[1]


def test_a_non_isolated_prefix_is_rejected_even_with_the_label() -> None:
    impostor = ("sio-purchase-copy", "127.0.0.1:18107->8000/tcp", True)
    with pytest.raises(guard.IsolationError):
        guard.check_targets({"purchase": "http://127.0.0.1:18107"}, environ=ISOLATED, runner=docker(impostor))
    with pytest.raises(guard.IsolationError, match="pila aislada"):
        guard.check_targets({"purchase": "http://127.0.0.1:18107"},
                            environ={"SIO_TEST_TARGET": "isolated", "SIO_INTEGRATION_CONTAINER_PREFIX": "sio-"},
                            runner=docker(ISOLATED_PU))


def test_docker_unavailable_fails_closed(monkeypatch) -> None:
    def broken(args):
        raise guard.IsolationError("Docker no responde")
    with pytest.raises(guard.IsolationError, match="Docker no responde"):
        guard.check_targets({"purchase": "http://127.0.0.1:18107"}, environ=ISOLATED, runner=broken)


def test_container_operations_only_on_isolated_containers() -> None:
    run = docker(labels={"sio-it-purchase-db": "true", "sio-purchase-db": ""})
    assert guard.check_container("sio-it-purchase-db", environ=ISOLATED, runner=run) == "sio-it-purchase-db"
    with pytest.raises(guard.IsolationError):
        guard.check_container("sio-purchase-db", environ=ISOLATED, runner=run)
    with pytest.raises(guard.IsolationError):
        guard.check_container("sio-it-purchase-db", environ={}, runner=run)


def test_messages_do_not_leak_secrets() -> None:
    secret = "secreto-sintetico"
    with pytest.raises(guard.IsolationError) as error:
        guard.check_targets({"purchase": f"http://usuario:{secret}@127.0.0.1:8107"}, environ=ISOLATED,
                            runner=docker(PERSISTENT))
    assert secret not in str(error.value)
