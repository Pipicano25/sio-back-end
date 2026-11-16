import logging

import pytest
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from sio_contract_read import cause_of, contract_errors


class Unavailable(Exception):
    def __init__(self, cause):
        super().__init__("no disponible")
        self.cause = cause


class FakeDriverError(Exception):
    def __init__(self, sqlstate, message):
        super().__init__(message)
        self.sqlstate = sqlstate


def wrap(sqlstate, message="postgresql://lector:secreto@db/x falló"):
    return DBAPIError("SELECT secreto", {"p": "secreto"}, FakeDriverError(sqlstate, message))


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (wrap("57014"), "tiempo_agotado"),
        (wrap("42501"), "permiso_denegado"),
        (PoolTimeout("QueuePool limit"), "pool_agotado"),
        (OperationalError("SELECT 1", {}, ConnectionRefusedError("refused")), "error_base:ConnectionRefusedError"),
    ],
)
def test_cause_of(exc, expected):
    assert cause_of(exc) == expected


def test_contract_errors_raises_consumer_exception_without_chain(caplog):
    caplog.set_level(logging.WARNING, logger="sio_contract_read")
    with pytest.raises(Unavailable) as info:
        with contract_errors(Unavailable, dependency="product-catalog"):
            raise wrap("57014")
    assert info.value.cause == "tiempo_agotado"
    assert info.value.__cause__ is None
    assert info.value.__suppress_context__ is True
    assert "secreto" not in caplog.text
    assert "dependencia=product-catalog causa=tiempo_agotado" in caplog.text


def test_contract_errors_lets_other_exceptions_through():
    with pytest.raises(KeyError):
        with contract_errors(Unavailable):
            raise KeyError("x")


def test_contract_errors_passes_when_no_error():
    with contract_errors(Unavailable):
        value = 1
    assert value == 1
