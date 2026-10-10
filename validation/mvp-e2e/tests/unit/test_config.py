"""T006 — Configuración de la suite (sio_mvp.config)."""

from pathlib import Path

import pytest

from sio_mvp import config

pytestmark = pytest.mark.unit

PORT_MAP = {
    "party-identity": 8101,
    "geography": 8102,
    "product-catalog": 8103,
    "operational-context": 8104,
    "payment-reference": 8105,
    "commercial-relationship": 8106,
    "purchase": 8107,
    "sales": 8108,
    "inventory": 8109,
    "audit": 8110,
}


def write_env(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


def test_default_urls_use_loopback_and_port_map(tmp_path):
    settings = config.load_settings(environ={}, env_file=tmp_path / "missing.env")
    assert {service.key for service in config.SERVICES} == set(PORT_MAP)
    for key, port in PORT_MAP.items():
        assert settings.service_url(key) == f"http://127.0.0.1:{port}"
    assert settings.token_url == "http://127.0.0.1:8081/realms/sio/protocol/openid-connect/token"


def test_api_base_adds_prefix_only_where_the_service_uses_it(tmp_path):
    settings = config.load_settings(environ={}, env_file=tmp_path / "missing.env")
    assert settings.api_base("sales") == "http://127.0.0.1:8108/api/v1"
    assert settings.api_base("geography") == "http://127.0.0.1:8102"
    assert settings.api_base("payment-reference") == "http://127.0.0.1:8105"


def test_service_url_can_be_overridden(tmp_path):
    environ = {
        "SIO_MVP_SALES_URL": "http://otro-host:9999/",
        "SIO_MVP_PARTY_IDENTITY_URL": "http://pi:1",
        "SIO_MVP_KEYCLOAK_TOKEN_URL": "http://kc/token",
    }
    settings = config.load_settings(environ=environ, env_file=tmp_path / "missing.env")
    assert settings.service_url("sales") == "http://otro-host:9999"
    assert settings.service_url("party-identity") == "http://pi:1"
    assert settings.service_url("purchase") == "http://127.0.0.1:8107"
    assert settings.token_url == "http://kc/token"


def test_secrets_come_from_environment_first_then_env_file(tmp_path):
    env_file = write_env(
        tmp_path,
        "# comentario\nKEYCLOAK_TEST_USER_PASSWORD=desde-archivo\nSALES_SERVICE_CLIENT_SECRET='s3cr3t'\n",
    )
    settings = config.load_settings(environ={"KEYCLOAK_TEST_USER_PASSWORD": "desde-entorno"}, env_file=env_file)
    assert settings.secret("KEYCLOAK_TEST_USER_PASSWORD").reveal() == "desde-entorno"
    assert settings.secret("SALES_SERVICE_CLIENT_SECRET").reveal() == "s3cr3t"
    assert settings.secret("PURCHASE_SERVICE_CLIENT_SECRET") is None


def test_secret_values_never_appear_in_repr_or_str(tmp_path):
    env_file = write_env(tmp_path, "KEYCLOAK_TEST_USER_PASSWORD=valor-muy-secreto\n")
    settings = config.load_settings(environ={}, env_file=env_file)
    secret = settings.secret("KEYCLOAK_TEST_USER_PASSWORD")
    for text in (repr(secret), str(secret), repr(settings), str(settings), f"{secret}"):
        assert "valor-muy-secreto" not in text


def test_sensitive_values_lists_secrets_passwords_and_tokens(tmp_path):
    env_file = write_env(
        tmp_path,
        "A_PASSWORD=p1\nB_CLIENT_SECRET=s1\nC_TOKEN=t1\nSALES_DB_PORT=5447\nEMPTY_PASSWORD=\n",
    )
    settings = config.load_settings(environ={}, env_file=env_file)
    assert settings.sensitive_values() == {"p1", "s1", "t1"}


def test_audit_wait_defaults_to_backoff_max_plus_60(tmp_path):
    settings = config.load_settings(environ={}, env_file=tmp_path / "missing.env")
    assert settings.audit_wait_seconds == 360.0
    settings = config.load_settings(
        environ={"AUDIT_OUTBOX_BACKOFF_MAX_SECONDS": "30"}, env_file=tmp_path / "missing.env"
    )
    assert settings.audit_wait_seconds == 90.0
    settings = config.load_settings(environ={"SIO_MVP_AUDIT_WAIT_SECONDS": "15"}, env_file=tmp_path / "missing.env")
    assert settings.audit_wait_seconds == 15.0


def test_guide_write_flag(tmp_path):
    assert not config.load_settings(environ={}, env_file=tmp_path / "x").guide_write
    assert config.load_settings(environ={"SIO_MVP_GUIDE_WRITE": "1"}, env_file=tmp_path / "x").guide_write


def test_managed_containers_cover_services_databases_workers_reconcilers_and_keycloak():
    containers = config.managed_containers()
    for key in PORT_MAP:
        assert f"sio-{key}-service" in containers
        assert f"sio-{key}-db" in containers
    workers = [name for name in containers if name.endswith("-audit-outbox-worker")]
    assert sorted(workers) == sorted(
        f"sio-{key}-audit-outbox-worker"
        for key in (
            "operational-context",
            "commercial-relationship",
            "party-identity",
            "product-catalog",
            "inventory",
            "purchase",
            "sales",
        )
    )
    assert "sio-purchase-reconciler" in containers
    assert "sio-sales-reconciler" in containers
    assert "sio-keycloak" in containers
    assert len(containers) == len(set(containers)) == 10 + 10 + 7 + 2 + 1
