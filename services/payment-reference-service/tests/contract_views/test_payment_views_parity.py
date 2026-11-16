"""Paridad y acceso de ``v1_payment_methods`` y ``v1_payment_condition_types`` (spec 025, T037 y T041).

- Cada columna de la vista coincide con el mismo campo del GET por id, para filas activas e inactivas.
- Un id inexistente no tiene fila en la vista, como el ``404`` del GET.
- Con ``contract/grants.yaml``, el rol lector de Sales lee ``v1_payment_methods`` y nada más: ni la vista no
  declarada ni las tablas de ``public``, y su transacción es de solo lectura.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from payment_reference_service.infrastructure.database import engine
from tests.conftest import CONDITION_TYPES, METHODS

SERVICE_ROOT = Path(__file__).resolve().parents[2]
GRANTS = SERVICE_ROOT / "contract" / "grants.yaml"


def _row(view: str, row_id: str) -> dict | None:
    with engine.connect() as connection:
        row = connection.execute(text(f"SELECT * FROM contract.{view} WHERE id = :id"), {"id": row_id}).mappings().first()
    if row is None:
        return None
    return {key: (str(value) if value is not None and not isinstance(value, str) else value) for key, value in row.items()}


def _method(admin, code: str, status: str = "ACTIVE") -> dict:
    response = admin.post(
        METHODS,
        json={"code": code, "name": f"Método {code}", "method_type": "CASH", "requires_reference": False, "status": status},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_payment_methods_view_matches_get(admin):
    active = _method(admin, "EFECTIVO_V1")
    inactive = _method(admin, "TARJETA_V1", status="INACTIVE")

    for method in (active, inactive):
        body = admin.get(f"{METHODS}/{method['id']}").json()
        view = _row("v1_payment_methods", method["id"])
        assert list(view) == ["id", "code", "name", "status"]
        for column in view:
            assert view[column] == body[column], column

    assert admin.get(f"{METHODS}/{uuid4()}").status_code == 404
    assert _row("v1_payment_methods", str(uuid4())) is None


def test_payment_condition_types_view_matches_get(admin):
    active = admin.post(CONDITION_TYPES, json={"code": "CONTADO_V1", "name": "Contado"}).json()
    inactive = admin.post(CONDITION_TYPES, json={"code": "CREDITO_V1", "name": "Crédito"}).json()
    response = admin.post(f"{CONDITION_TYPES}/{inactive['id']}/deactivate", json={"version": inactive["version"]})
    assert response.status_code == 200, response.text

    for item in (active, inactive):
        body = admin.get(f"{CONDITION_TYPES}/{item['id']}").json()
        view = _row("v1_payment_condition_types", item["id"])
        assert list(view) == ["id", "code", "status"]
        for column in view:
            assert view[column] == body[column], column
    assert _row("v1_payment_condition_types", inactive["id"])["status"] == "INACTIVE"
    assert _row("v1_payment_condition_types", str(uuid4())) is None


@pytest.fixture
def sales_reader():
    from sio_contract_read.testing import provision_reader

    url = provision_reader(
        engine.url.render_as_string(hide_password=False), GRANTS, "sales", secrets.token_urlsafe(24)
    )
    reader = create_engine(url)
    yield reader
    reader.dispose()


def _denied(reader, statement: str) -> bool:
    try:
        with reader.connect() as connection:
            connection.execute(text(statement))
    except DBAPIError as error:
        return "permission denied" in str(error.orig) or "read-only transaction" in str(error.orig)
    return False


def test_sales_reader_reads_only_its_views(admin, sales_reader):
    method = _method(admin, "EFECTIVO_LECTOR")

    with sales_reader.connect() as connection:
        rows = connection.execute(text("SELECT id, code FROM contract.v1_payment_methods")).all()
    assert [(str(row.id), row.code) for row in rows] == [(method["id"], "EFECTIVO_LECTOR")]

    assert _denied(sales_reader, "SELECT 1 FROM contract.v1_payment_condition_types LIMIT 1")
    assert _denied(sales_reader, "SELECT 1 FROM public.global_payment_methods LIMIT 1")
    assert _denied(sales_reader, "SELECT 1 FROM public.global_payment_condition_types LIMIT 1")
    assert _denied(sales_reader, "CREATE TEMP TABLE intento (id int)")


def test_downgrade_removes_views_and_schema_and_upgrade_restores_them():
    from alembic import command

    from tests.conftest import alembic_config

    def contract_views() -> list[str]:
        with engine.connect() as connection:
            return connection.execute(
                text("SELECT table_name FROM information_schema.views WHERE table_schema = 'contract' ORDER BY 1")
            ).scalars().all()

    config = alembic_config()
    command.downgrade(config, "-1")
    try:
        assert contract_views() == []
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1 FROM pg_namespace WHERE nspname = 'contract'")).first() is None
    finally:
        command.upgrade(config, "head")
    assert contract_views() == ["v1_payment_condition_types", "v1_payment_methods"]
