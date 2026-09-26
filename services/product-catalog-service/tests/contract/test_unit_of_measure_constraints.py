"""Restricciones de `global_units_of_measure` (RC-01)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

INSERT = text(
    "INSERT INTO global_units_of_measure (id, code, name, symbol, measurement_type,"
    " allows_decimals, status, version, created_at, updated_at, created_by, updated_by)"
    " VALUES (:id, :code, 'Nombre', 's', :measurement_type, true, :status, 1, :now, :now, 't', 't')"
)


def _insert(session: Session, code: str, measurement_type: str = "MASS", status: str = "ACTIVE") -> None:
    session.execute(
        INSERT,
        {
            "id": uuid4(),
            "code": code,
            "measurement_type": measurement_type,
            "status": status,
            "now": datetime.now(UTC),
        },
    )
    session.flush()


def test_code_unique(db_session: Session) -> None:
    _insert(db_session, "KG")
    with pytest.raises(IntegrityError, match="uq_global_units_of_measure_code"):
        _insert(db_session, "KG")


def test_code_must_be_normalized(db_session: Session) -> None:
    with pytest.raises(IntegrityError, match="ck_global_units_of_measure_code_normalized"):
        _insert(db_session, "kg")


def test_measurement_type_check(db_session: Session) -> None:
    with pytest.raises(IntegrityError, match="ck_global_units_of_measure_measurement_type"):
        _insert(db_session, "HR", measurement_type="TIME")


def test_status_check(db_session: Session) -> None:
    with pytest.raises(IntegrityError, match="ck_global_units_of_measure_status"):
        _insert(db_session, "LB", status="DELETED")
