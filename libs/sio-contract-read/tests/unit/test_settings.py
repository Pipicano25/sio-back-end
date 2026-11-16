import pytest

from sio_contract_read import CONTRACT, HTTP, ContractReadConfigError, ContractReadSettings

URL = "postgresql+psycopg://lector:secreto@db:5432/catalogo"


def build(env, timeout=5):
    return ContractReadSettings.from_env("PRODUCT_CATALOG", timeout_seconds=timeout, env=env)


def test_defaults_to_http_without_url():
    settings = build({})
    assert settings.source == HTTP
    assert not settings.uses_contract
    assert settings.database_url is None
    assert (settings.pool_size, settings.max_overflow, settings.connect_timeout_seconds) == (1, 2, 2)


def test_contract_requires_url():
    with pytest.raises(ContractReadConfigError, match="PRODUCT_CATALOG_CONTRACT_DATABASE_URL"):
        build({"PRODUCT_CATALOG_READ_SOURCE": "contract"})


def test_contract_requires_psycopg_scheme():
    with pytest.raises(ContractReadConfigError, match="postgresql\\+psycopg://"):
        build({"PRODUCT_CATALOG_READ_SOURCE": "contract", "PRODUCT_CATALOG_CONTRACT_DATABASE_URL": "postgres://x/y"})


def test_contract_accepts_valid_values():
    settings = build(
        {
            "PRODUCT_CATALOG_READ_SOURCE": " Contract ",
            "PRODUCT_CATALOG_CONTRACT_DATABASE_URL": URL,
            "CONTRACT_READ_POOL_SIZE": "3",
            "CONTRACT_READ_MAX_OVERFLOW": "0",
            "CONTRACT_READ_CONNECT_TIMEOUT_SECONDS": "10",
        },
        timeout=10,
    )
    assert settings.source == CONTRACT and settings.uses_contract
    assert settings.database_url == URL
    assert (settings.pool_size, settings.max_overflow, settings.connect_timeout_seconds) == (3, 0, 10)
    assert settings.timeout_seconds == 10.0


def test_http_ignores_url_validation():
    assert build({"PRODUCT_CATALOG_CONTRACT_DATABASE_URL": "no-valida"}).source == HTTP


def test_invalid_source_names_variable():
    with pytest.raises(ContractReadConfigError, match="PRODUCT_CATALOG_READ_SOURCE"):
        build({"PRODUCT_CATALOG_READ_SOURCE": "grpc"})


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CONTRACT_READ_POOL_SIZE", "0"),
        ("CONTRACT_READ_POOL_SIZE", "11"),
        ("CONTRACT_READ_MAX_OVERFLOW", "-1"),
        ("CONTRACT_READ_MAX_OVERFLOW", "11"),
        ("CONTRACT_READ_CONNECT_TIMEOUT_SECONDS", "0"),
        ("CONTRACT_READ_CONNECT_TIMEOUT_SECONDS", "abc"),
    ],
)
def test_out_of_range_names_variable(name, value):
    with pytest.raises(ContractReadConfigError, match=name):
        build({name: value})


def test_timeout_must_be_positive():
    with pytest.raises(ContractReadConfigError):
        build({}, timeout=0)


def test_error_never_contains_url():
    env = {"PRODUCT_CATALOG_READ_SOURCE": "contract", "PRODUCT_CATALOG_CONTRACT_DATABASE_URL": "mysql://u:secreto@h/d"}
    with pytest.raises(ContractReadConfigError) as info:
        build(env)
    assert "secreto" not in str(info.value)
