import pytest

from sio_contract_read import ContractReadConfigError, ContractReadSettings, chunked, connect_options, create_contract_engine

URL = "postgresql+psycopg://lector:secreto@db:5432/catalogo"


def contract_settings(**overrides):
    values = dict(prefix="PRODUCT_CATALOG", source="contract", database_url=URL, timeout_seconds=5.0)
    values.update(overrides)
    return ContractReadSettings(**values)


def test_connect_options_set_timeout_read_only_and_name():
    options = connect_options(contract_settings(timeout_seconds=2.5), "sales-service")
    assert options == "-c statement_timeout=2500 -c default_transaction_read_only=on -c application_name=sales-service"


def test_connect_options_sanitizes_application_name():
    options = connect_options(contract_settings(), "sales service; DROP")
    assert "application_name=salesserviceDROP" in options
    assert ";" not in options and " DROP" not in options


def test_engine_uses_small_pool_and_timeouts():
    engine = create_contract_engine(contract_settings(pool_size=2, max_overflow=1), application_name="sales-service")
    try:
        pool = engine.pool
        assert pool.size() == 2
        assert pool._max_overflow == 1
        assert pool._timeout == 5.0
        assert pool._pre_ping is True
    finally:
        engine.dispose()


def test_engine_requires_contract_source():
    settings = ContractReadSettings(prefix="PRODUCT_CATALOG", source="http", database_url=None, timeout_seconds=5)
    with pytest.raises(ContractReadConfigError):
        create_contract_engine(settings, application_name="sales-service")


def test_chunked_keeps_order():
    assert chunked(range(5), 2) == [[0, 1], [2, 3], [4]]
    assert chunked([], 100) == []
    assert len(chunked(range(250))) == 3
