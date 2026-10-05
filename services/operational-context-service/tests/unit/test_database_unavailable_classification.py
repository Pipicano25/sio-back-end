"""Clasificación de "base de datos no disponible" (feature 009, FR-008).

Solo la pérdida o indisponibilidad de la conexión con PostgreSQL se traduce a `503`; los demás errores
de PostgreSQL (aunque psycopg 3 los clasifique como `OperationalError`) conservan su comportamiento.
"""

import psycopg.errors as pg
import pytest
from sqlalchemy.exc import IntegrityError, InterfaceError, OperationalError

from operational_context_service.api.errors import is_database_unavailable


def _operational(orig: Exception, **kwargs) -> OperationalError:
    return OperationalError("SELECT 1", {}, orig, **kwargs)


@pytest.mark.parametrize(
    "exc",
    [
        InterfaceError("SELECT 1", {}, pg.InterfaceError("the connection is closed")),
        _operational(pg.OperationalError("connection refused")),
        _operational(Exception("server closed the connection unexpectedly")),
        _operational(pg.QueryCanceled("canceling statement"), connection_invalidated=True),
        _operational(pg.ConnectionFailure("connection failure")),
        _operational(pg.AdminShutdown("terminating connection due to administrator command")),
        _operational(pg.CrashShutdown("terminating connection because of crash of another server process")),
        _operational(pg.CannotConnectNow("the database system is starting up")),
    ],
    ids=[
        "interface-error",
        "sin-sqlstate",
        "excepcion-sin-sqlstate",
        "conexion-invalidada",
        "08006",
        "57P01",
        "57P02",
        "57P03",
    ],
)
def test_connection_loss_is_database_unavailable(exc) -> None:
    assert is_database_unavailable(exc) is True


@pytest.mark.parametrize(
    "orig",
    [
        pg.DeadlockDetected("deadlock detected"),
        pg.SerializationFailure("could not serialize access"),
        pg.QueryCanceled("canceling statement due to statement timeout"),
        pg.LockNotAvailable("could not obtain lock"),
    ],
    ids=["40P01", "40001", "57014", "55P03"],
)
def test_other_postgresql_errors_are_not_database_unavailable(orig) -> None:
    assert orig.sqlstate is not None
    assert is_database_unavailable(_operational(orig)) is False


def test_non_connection_errors_are_not_database_unavailable() -> None:
    assert is_database_unavailable(IntegrityError("INSERT", {}, pg.UniqueViolation("duplicate"))) is False
    assert is_database_unavailable(ValueError("otro error")) is False
