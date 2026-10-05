"""Carga inicial idempotente con versión (FR-031, SC-005)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from payment_reference_service.infrastructure.database import engine

SERVICE_ROOT = Path(__file__).resolve().parents[2]


def _seed_load() -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "payment_reference_service.seed", "load"],
        cwd=SERVICE_ROOT,
        env={**os.environ},
        capture_output=True,
        text=True,
        check=False,
    )


def _rows(sql: str):
    with engine.connect() as connection:
        return connection.execute(text(sql)).all()


def test_seed_load_twice_is_idempotent_with_version_one():
    first = _seed_load()
    second = _seed_load()

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    types = _rows("SELECT code, status, version FROM global_payment_condition_types ORDER BY code")
    assert [tuple(row) for row in types] == [
        ("CASH", "ACTIVE", 1),
        ("CREDIT", "ACTIVE", 1),
        ("FINANCING", "ACTIVE", 1),
    ]
    assert _rows("SELECT count(*) FROM global_payment_methods")[0][0] == 7
