"""Fixtures de `sio-audit`.

Las pruebas de contrato usan una base PostgreSQL de pruebas como base del "emisor"
(`SIO_AUDIT_TEST_DATABASE_URL`; por defecto la base de pruebas de audit-service,
`sio-audit-test-db`, perfil `test`). Crean y eliminan solo la tabla `audit_outbox`.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url

from sio_audit.outbox import audit_outbox_table

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)

DEFAULT_URL = (
    "postgresql+psycopg://sio_audit_test:sio_audit_test_dev_change_me@127.0.0.1:55451/sio_audit_test"
)


@pytest.fixture(scope="session")
def outbox_database_url() -> str:
    url = os.getenv("SIO_AUDIT_TEST_DATABASE_URL", DEFAULT_URL).strip()
    if "test" not in (make_url(url).database or "").lower():
        raise RuntimeError("SIO_AUDIT_TEST_DATABASE_URL debe apuntar a una base exclusiva de pruebas.")
    return url


@pytest.fixture(scope="session")
def outbox_engine(outbox_database_url: str) -> Generator[Engine, None, None]:
    engine = create_engine(outbox_database_url, pool_pre_ping=True)
    metadata = MetaData()
    audit_outbox_table(metadata)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS audit_outbox"))
    metadata.create_all(engine)
    try:
        yield engine
    finally:
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS audit_outbox"))
        engine.dispose()


@pytest.fixture
def clean_outbox(outbox_engine: Engine) -> Engine:
    with outbox_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE audit_outbox"))
    return outbox_engine
