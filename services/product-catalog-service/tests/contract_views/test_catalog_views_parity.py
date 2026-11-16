"""Paridad de ``v1_products``, ``v1_presentations`` y ``v1_units_of_measure`` (spec 025, T034).

Para ids activos, inactivos e inexistentes, cada columna de la vista coincide con el mismo campo del GET del
propietario y de su ``batch-lookup``. Un id inexistente no tiene fila en la vista, el GET responde 404 y el
``batch-lookup`` lo devuelve con ``found: false``.

Además comprueba, con ``contract/grants.yaml`` y ``sio_contract_read.testing.provision_reader``, que el rol lector de
Sales lee las vistas y no las tablas de ``public`` (contracts/reader-roles.md).
"""

from __future__ import annotations

import secrets
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests import factories

SERVICE_DIR = Path(__file__).resolve().parents[2]
GRANTS = SERVICE_DIR / "contract" / "grants.yaml"

PRODUCT_COLUMNS = ("id", "status", "base_unit_id")
PRESENTATION_COLUMNS = ("id", "global_product_id", "code", "name", "status", "base_quantity")
UNIT_COLUMNS = ("id", "code", "name", "status", "measurement_type", "allows_decimals")


def _normalize(value):
    """Lleva un valor de la vista o de la API a una forma comparable (UUID y decimales como texto canónico)."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return value.normalize()
    return value


def _api_value(column: str, value):
    if column == "base_quantity" and value is not None:
        return Decimal(str(value)).normalize()
    return value


def _view_row(connection, view: str, entity_id) -> dict | None:
    row = connection.execute(text(f"SELECT * FROM contract.{view} WHERE id = :id"), {"id": str(entity_id)}).mappings().first()
    return None if row is None else {key: _normalize(value) for key, value in row.items()}


def _assert_same(view: dict, body: dict, columns: tuple[str, ...], label: str) -> None:
    assert set(view) == set(columns), f"{label}: columnas de la vista"
    for column in columns:
        assert view[column] == _api_value(column, body[column]), f"{label}.{column}"


@pytest.fixture
def catalog(session_factory):
    """Unidades, productos y presentaciones activos e inactivos."""
    kg = factories.unit(session_factory, "KG", allows_decimals=True)
    und = factories.unit(session_factory, "UND")
    old = factories.unit(session_factory, "OLD", status="INACTIVE")
    active = factories.product(session_factory, kg.id, "Arroz blanco 500 g")
    inactive = factories.product(session_factory, und.id, "Producto retirado", status="INACTIVE")
    presentations = [
        factories.presentation(session_factory, active.id, "UNIDAD", is_base=True),
        factories.presentation(session_factory, active.id, "CAJA", base_quantity=Decimal("12.5")),
        factories.presentation(session_factory, active.id, "VIEJA", status="INACTIVE"),
        factories.presentation(session_factory, inactive.id, "UNIDAD"),
    ]
    return {
        "units": [kg.id, und.id, old.id],
        "products": [active.id, inactive.id],
        "presentations": [item.id for item in presentations],
    }


def test_products_match_get_and_batch_lookup(api, catalog, test_engine):
    missing = uuid4()
    ids = [*catalog["products"], missing]
    lookup = {item["id"]: item for item in api.post(
        "/api/v1/products/batch-lookup", json={"ids": [str(value) for value in ids]}
    ).json()["items"]}

    with test_engine.connect() as connection:
        for product_id in catalog["products"]:
            response = api.get(f"/api/v1/products/{product_id}")
            assert response.status_code == 200
            view = _view_row(connection, "v1_products", product_id)
            _assert_same(view, response.json(), PRODUCT_COLUMNS, f"producto {product_id}")
            item = lookup[str(product_id)]
            assert item["found"] is True
            assert view["status"] == item["status"]

        assert _view_row(connection, "v1_products", missing) is None
        assert api.get(f"/api/v1/products/{missing}").status_code == 404
        assert lookup[str(missing)]["found"] is False


def test_presentations_match_get_and_batch_lookup(api, catalog, test_engine):
    missing = uuid4()
    ids = [*catalog["presentations"], missing]
    lookup = {item["id"]: item for item in api.post(
        "/api/v1/presentations/batch-lookup", json={"ids": [str(value) for value in ids]}
    ).json()["items"]}

    with test_engine.connect() as connection:
        statuses = set()
        for presentation_id in catalog["presentations"]:
            response = api.get(f"/api/v1/presentations/{presentation_id}")
            assert response.status_code == 200
            view = _view_row(connection, "v1_presentations", presentation_id)
            _assert_same(view, response.json(), PRESENTATION_COLUMNS, f"presentación {presentation_id}")
            item = lookup[str(presentation_id)]
            assert item["found"] is True
            _assert_same(view, item, PRESENTATION_COLUMNS, f"lookup {presentation_id}")
            statuses.add(view["status"])
        assert statuses == {"ACTIVE", "INACTIVE"}

        assert _view_row(connection, "v1_presentations", missing) is None
        assert api.get(f"/api/v1/presentations/{missing}").status_code == 404
        assert lookup[str(missing)]["found"] is False

        image_columns = connection.execute(
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_schema = 'contract' AND table_name = 'v1_presentations' AND column_name LIKE '%image%'")
        ).scalars().all()
        assert image_columns == []


def test_units_of_measure_match_get_and_batch_lookup(api, catalog, test_engine):
    missing = uuid4()
    ids = [*catalog["units"], missing]
    lookup = {item["id"]: item for item in api.post(
        "/api/v1/units-of-measure/batch-lookup", json={"ids": [str(value) for value in ids]}
    ).json()["items"]}

    with test_engine.connect() as connection:
        for unit_id in catalog["units"]:
            response = api.get(f"/api/v1/units-of-measure/{unit_id}")
            assert response.status_code == 200
            view = _view_row(connection, "v1_units_of_measure", unit_id)
            _assert_same(view, response.json(), UNIT_COLUMNS, f"unidad {unit_id}")
            item = lookup[str(unit_id)]
            assert item["found"] is True
            _assert_same(view, item, UNIT_COLUMNS, f"lookup {unit_id}")

        assert _view_row(connection, "v1_units_of_measure", missing) is None
        assert api.get(f"/api/v1/units-of-measure/{missing}").status_code == 404
        assert lookup[str(missing)]["found"] is False


# --------------------------------------------------------------------------- roles de lectura (grants.yaml)


def _denied(engine, sql: str) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text(sql))
    except DBAPIError:
        return True
    return False


def test_sales_reader_reads_views_and_not_public_tables(test_database_url, test_engine):
    testing = pytest.importorskip("sio_contract_read.testing")
    url = testing.provision_reader(test_database_url, GRANTS, "sales", secrets.token_urlsafe(24))
    reader = create_engine(url, pool_pre_ping=True)
    try:
        with reader.connect() as connection:
            for view in ("v1_products", "v1_presentations", "v1_units_of_measure"):
                connection.execute(text(f"SELECT * FROM contract.{view} LIMIT 1")).all()
        for table in ("global_products", "global_product_presentations", "global_units_of_measure", "product_assets"):
            assert _denied(reader, f"SELECT 1 FROM public.{table} LIMIT 1"), table
        assert _denied(reader, "CREATE TEMP TABLE sio_contract_probe (x int)")
    finally:
        reader.dispose()


def test_reader_only_reads_declared_views(test_database_url, test_engine):
    """PIQ solo declara ``v1_units_of_measure``: no lee ``v1_products`` ni ``v1_presentations``."""
    testing = pytest.importorskip("sio_contract_read.testing")
    url = testing.provision_reader(test_database_url, GRANTS, "product-inventory-query", secrets.token_urlsafe(24))
    reader = create_engine(url, pool_pre_ping=True)
    try:
        with reader.connect() as connection:
            connection.execute(text("SELECT * FROM contract.v1_units_of_measure LIMIT 1")).all()
        assert _denied(reader, "SELECT 1 FROM contract.v1_products LIMIT 1")
        assert _denied(reader, "SELECT 1 FROM contract.v1_presentations LIMIT 1")
    finally:
        reader.dispose()
