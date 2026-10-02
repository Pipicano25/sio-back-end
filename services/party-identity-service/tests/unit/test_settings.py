"""Pruebas de la configuración de Operational Context (FR-100, FR-028a)."""

import pytest

from party_identity_service.config import load_settings


@pytest.fixture
def base_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:1/db")
    monkeypatch.delenv("OPERATIONAL_CONTEXT_SERVICE_BASE_URL", raising=False)
    monkeypatch.delenv("OPERATIONAL_CONTEXT_TIMEOUT_SECONDS", raising=False)
    return monkeypatch


def test_operational_context_defaults(base_env: pytest.MonkeyPatch) -> None:
    settings = load_settings()

    assert settings.operational_context_service_base_url == "http://localhost:8004/api/v1"
    assert settings.operational_context_timeout_seconds == 5.0


def test_operational_context_values_from_environment(base_env: pytest.MonkeyPatch) -> None:
    base_env.setenv("OPERATIONAL_CONTEXT_SERVICE_BASE_URL", "http://oc:8000/api/v1/")
    base_env.setenv("OPERATIONAL_CONTEXT_TIMEOUT_SECONDS", "2.5")

    settings = load_settings()

    assert settings.operational_context_service_base_url == "http://oc:8000/api/v1"
    assert settings.operational_context_timeout_seconds == 2.5


@pytest.mark.parametrize("value", ["0", "-1", "abc"])
def test_operational_context_timeout_must_be_positive(
    base_env: pytest.MonkeyPatch,
    value: str,
) -> None:
    base_env.setenv("OPERATIONAL_CONTEXT_TIMEOUT_SECONDS", value)

    with pytest.raises(RuntimeError):
        load_settings()
