"""Configuración (T004; FR-022-133, FR-022-146, FR-022-147, RNF-022-3)."""

from __future__ import annotations

import pytest

from product_inventory_query_service.config import load_settings
from tests.conftest import TEST_CURSOR_SECRET, build_test_settings

REQUIRED_ENV = {
    "OPERATIONAL_CONTEXT_SERVICE_BASE_URL": "http://oc/api/v1",
    "COMMERCIAL_RELATIONSHIP_SERVICE_BASE_URL": "http://cr/api/v1",
    "PRODUCT_CATALOG_SERVICE_BASE_URL": "http://pc/api/v1",
    "INVENTORY_SERVICE_BASE_URL": "http://in/api/v1",
    "KEYCLOAK_TOKEN_URL": "http://kc/token",
    "PIQS_CLIENT_SECRET": "client-secret",
    "PIQS_CURSOR_SECRET": TEST_CURSOR_SECRET,
}


@pytest.fixture
def env(monkeypatch):
    for name in list(REQUIRED_ENV) + ["PIQS_CURSOR_SECRET_PREVIOUS", "PIQS_WORK_TIME_SECONDS"]:
        monkeypatch.delenv(name, raising=False)
    for name, value in REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


def test_defaults_match_research_r17(env) -> None:
    settings = load_settings()
    assert settings.dependency_timeout_seconds == 3.0
    assert settings.request_budget_seconds == 8.0
    assert settings.work_time_seconds == 5.0
    assert settings.max_batches_per_request == 5
    assert (settings.batch_min, settings.batch_factor, settings.batch_max) == (20, 2, 40)
    assert settings.cursor_ttl_seconds == 900
    assert settings.reference_cache_seconds == 300.0
    assert settings.client_id == "product-inventory-query-service"
    assert settings.docs_enabled is False


@pytest.mark.parametrize("missing", sorted(REQUIRED_ENV))
def test_missing_required_variable_fails_at_startup(env, missing) -> None:
    env.delenv(missing)
    with pytest.raises(RuntimeError, match=missing):
        load_settings()


def test_short_cursor_secret_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="32 bytes"):
        build_test_settings(cursor_secret="corto")


def test_previous_cursor_secret_must_be_strong_and_distinct() -> None:
    with pytest.raises(RuntimeError, match="32 bytes"):
        build_test_settings(cursor_secret_previous="corto")
    with pytest.raises(RuntimeError, match="distinto"):
        build_test_settings(cursor_secret_previous=TEST_CURSOR_SECRET)
    assert build_test_settings(cursor_secret_previous="x" * 40).cursor_secret_previous == "x" * 40


def test_work_time_plus_one_call_must_fit_in_request_budget() -> None:
    """5 s de trabajo + 3 s de una llamada de enriquecimiento ≤ 8 s (RNF-022-3, FR-022-136)."""
    assert build_test_settings().request_budget_seconds == 8.0
    with pytest.raises(RuntimeError, match="PIQS_REQUEST_BUDGET_SECONDS"):
        build_test_settings(work_time_seconds=6.0)
    with pytest.raises(RuntimeError, match="PIQS_REQUEST_BUDGET_SECONDS"):
        build_test_settings(dependency_timeout_seconds=3.5)


def test_batch_bounds_are_validated() -> None:
    with pytest.raises(RuntimeError):
        build_test_settings(batch_min=50, batch_max=40)
    with pytest.raises(RuntimeError):
        build_test_settings(batch_max=101)


@pytest.mark.parametrize(("page_size", "expected"), [(1, 20), (5, 20), (10, 20), (15, 30), (20, 40)])
def test_batch_size_formula(page_size: int, expected: int) -> None:
    assert build_test_settings().batch_size(page_size) == expected


def test_repr_never_shows_secrets() -> None:
    settings = build_test_settings()
    text = repr(settings)
    assert TEST_CURSOR_SECRET not in text
    assert settings.client_secret not in text


def test_invalid_numbers_are_rejected(env) -> None:
    env.setenv("PIQS_WORK_TIME_SECONDS", "abc")
    with pytest.raises(RuntimeError, match="numérica"):
        load_settings()
