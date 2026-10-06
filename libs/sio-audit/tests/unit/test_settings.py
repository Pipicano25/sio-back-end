"""Configuración del worker y `--check` (R-12; T053)."""

from __future__ import annotations

import time

import pytest

from sio_audit.worker.__main__ import main
from sio_audit.worker.loop import backoff_seconds, heartbeat_is_fresh, write_heartbeat
from sio_audit.worker.settings import WorkerConfigurationError, WorkerSettings

REQUIRED = {
    "DATABASE_URL": "postgresql+psycopg://u:p@db:5432/x",
    "AUDIT_SERVICE_BASE_URL": "http://audit-service:8000/api/v1/",
    "KEYCLOAK_BASE_URL": "http://keycloak:8080",
    "KEYCLOAK_REALM": "sio",
    "AUDIT_CLIENT_ID": "inventory-service",
    "AUDIT_CLIENT_SECRET": "s",
}


def test_defaults() -> None:
    settings = WorkerSettings.from_env(REQUIRED)

    assert settings.audit_base_url == "http://audit-service:8000/api/v1"
    assert settings.poll_interval_seconds == 2.0
    assert settings.http_timeout_seconds == 5.0
    assert settings.backoff_initial_seconds == 1.0
    assert settings.backoff_factor == 2.0
    assert settings.backoff_max_seconds == 300.0
    assert settings.batch_size == 100
    assert settings.token_url == "http://keycloak:8080/realms/sio/protocol/openid-connect/token"
    assert "client_secret" not in repr(settings)


def test_overrides() -> None:
    settings = WorkerSettings.from_env(
        {
            **REQUIRED,
            "AUDIT_OUTBOX_POLL_INTERVAL_SECONDS": "0.5",
            "AUDIT_OUTBOX_HTTP_TIMEOUT_SECONDS": "3",
            "AUDIT_OUTBOX_BACKOFF_INITIAL_SECONDS": "2",
            "AUDIT_OUTBOX_BACKOFF_FACTOR": "3",
            "AUDIT_OUTBOX_BACKOFF_MAX_SECONDS": "60",
            "AUDIT_OUTBOX_BATCH_SIZE": "10",
        }
    )
    assert (settings.poll_interval_seconds, settings.backoff_factor, settings.batch_size) == (0.5, 3.0, 10)


@pytest.mark.parametrize("missing", sorted(REQUIRED))
def test_required_variables(missing: str) -> None:
    env = {key: value for key, value in REQUIRED.items() if key != missing}
    with pytest.raises(WorkerConfigurationError):
        WorkerSettings.from_env(env)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AUDIT_OUTBOX_BATCH_SIZE", "0"),
        ("AUDIT_OUTBOX_BATCH_SIZE", "101"),
        ("AUDIT_OUTBOX_POLL_INTERVAL_SECONDS", "0"),
        ("AUDIT_OUTBOX_BACKOFF_FACTOR", "0.5"),
        ("AUDIT_OUTBOX_BACKOFF_MAX_SECONDS", "0.5"),
        ("AUDIT_OUTBOX_HTTP_TIMEOUT_SECONDS", "x"),
    ],
)
def test_invalid_values(name: str, value: str) -> None:
    with pytest.raises(WorkerConfigurationError):
        WorkerSettings.from_env({**REQUIRED, name: value})


def test_backoff_formula() -> None:
    settings = WorkerSettings.from_env({**REQUIRED, "AUDIT_OUTBOX_BACKOFF_MAX_SECONDS": "10"})

    def exact(a, b):
        return 1.0

    assert [backoff_seconds(n, settings, rng=exact) for n in range(1, 7)] == [1, 2, 4, 8, 10, 10]
    assert backoff_seconds(1, settings, maximum=True, rng=exact) == 10
    assert backoff_seconds(10, settings, rng=lambda a, b: b) == 10  # el jitter nunca supera el tope


def test_check_uses_heartbeat(tmp_path, monkeypatch) -> None:
    heartbeat = tmp_path / "hb"
    env = {**REQUIRED, "AUDIT_OUTBOX_HEARTBEAT_FILE": str(heartbeat)}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    settings = WorkerSettings.from_env(env)

    assert main(["--check"]) == 1
    write_heartbeat(str(heartbeat))
    assert main(["--check"]) == 0
    assert not heartbeat_is_fresh(settings, now=time.time() + settings.heartbeat_max_age_seconds + 1)


def test_invalid_configuration_exits_with_2(monkeypatch) -> None:
    for key in REQUIRED:
        monkeypatch.delenv(key, raising=False)
    assert main([]) == 2
