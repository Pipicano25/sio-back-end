"""Paridad de ``v1_product_summaries``, ``v1_product_summary_categories`` y ``v1_product_summary_identifiers``
(spec 025, T072).

Para productos activos e inactivos, con y sin marca, con categorías e identificadores activos e inactivos, y para un
id inexistente, las vistas leídas como las lee el consumidor (``ORDER BY is_primary DESC, code`` en categorías e
``ORDER BY is_primary DESC, identifier_type, value`` en identificadores) dan exactamente los mismos datos, en el
mismo orden, que ``POST /products/summaries/batch-lookup`` (PC-1) **sin los campos de imagen**. Un id inexistente no
tiene fila y PC-1 lo devuelve con ``found: false``.

Además comprueba, con ``contract/grants.yaml``, que el rol lector de PIQ lee las tres vistas y no las tablas de
``public``.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests import factories

SERVICE_DIR = Path(__file__).resolve().parents[2]
GRANTS = SERVICE_DIR / "contract" / "grants.yaml"
URL = "/api/v1/products/summaries/batch-lookup"

SUMMARY_COLUMNS = {
    "id", "canonical_name", "product_type", "status", "brand_id", "brand_code", "brand_name",
    "base_unit_id", "base_unit_code", "base_unit_name",
}
CATEGORY_COLUMNS = {"global_product_id", "category_id", "code", "name", "is_primary"}
IDENTIFIER_COLUMNS = {"global_product_id", "identifier_type", "value", "is_primary", "global_product_presentation_id"}
IMAGE_FIELDS = {"has_image", "image_asset_id", "image_url"}

_SUMMARY = "SELECT * FROM contract.v1_product_summaries WHERE id = :id"
_CATEGORIES = (
    "SELECT * FROM contract.v1_product_summary_categories WHERE global_product_id = :id ORDER BY is_primary DESC, code"
)
_IDENTIFIERS = (
    "SELECT * FROM contract.v1_product_summary_identifiers WHERE global_product_id = :id"
    " ORDER BY is_primary DESC, identifier_type, value"
)


def _text(value):
    return str(value) if isinstance(value, UUID) else value


def _reference(row: dict, prefix: str) -> dict | None:
    if row[f"{prefix}_id"] is None:
        return None
    return {"id": str(row[f"{prefix}_id"]), "code": row[f"{prefix}_code"], "name": row[f"{prefix}_name"]}


def _from_views(connection, product_id) -> dict | None:
    """El resumen como lo reconstruye el consumidor desde las tres vistas, con la forma de PC-1."""
    summary = connection.execute(text(_SUMMARY), {"id": str(product_id)}).mappings().first()
    if summary is None:
        return None
    summary = dict(summary)
    assert set(summary) == SUMMARY_COLUMNS
    categories = [dict(row) for row in connection.execute(text(_CATEGORIES), {"id": str(product_id)}).mappings()]
    identifiers = [dict(row) for row in connection.execute(text(_IDENTIFIERS), {"id": str(product_id)}).mappings()]
    assert all(set(row) == CATEGORY_COLUMNS for row in categories)
    assert all(set(row) == IDENTIFIER_COLUMNS for row in identifiers)
    return {
        "id": str(summary["id"]),
        "found": True,
        "canonical_name": summary["canonical_name"],
        "product_type": summary["product_type"],
        "status": summary["status"],
        "brand": _reference(summary, "brand"),
        "base_unit": _reference(summary, "base_unit"),
        "categories": [
            {"id": str(row["category_id"]), "code": row["code"], "name": row["name"], "is_primary": row["is_primary"]}
            for row in categories
        ],
        "identifiers": [
            {"type": row["identifier_type"], "value": row["value"], "is_primary": row["is_primary"],
             "global_product_presentation_id": _text(row["global_product_presentation_id"])}
            for row in identifiers
        ],
    }


@pytest.fixture
def catalog(session_factory, test_engine):
    """Productos activo (con marca, categorías e identificadores en varios estados) e inactivo (sin marca)."""
    unit = factories.unit(session_factory, "TAB")
    brand = factories.brand(session_factory, "COLGATE", status="INACTIVE")
    active = factories.product(session_factory, unit.id, "Crema dental 100 ml", brand_id=brand.id)
    inactive = factories.product(session_factory, factories.unit(session_factory, "KG").id, "Retirado",
                                 status="INACTIVE")

    primary = factories.category(session_factory, "HIGIENE")
    zeta = factories.category(session_factory, "ZETA")
    alfa = factories.category(session_factory, "ALFA", status="INACTIVE")  # categoría inactiva, asociación activa
    retired = factories.category(session_factory, "RETIRADA")
    factories.product_category(session_factory, active.id, zeta.id, is_primary=False)
    factories.product_category(session_factory, active.id, primary.id, is_primary=True)
    factories.product_category(session_factory, active.id, alfa.id, is_primary=False)
    factories.product_category(session_factory, active.id, retired.id, is_primary=False, status="INACTIVE")
    factories.product_category(session_factory, inactive.id, zeta.id, is_primary=False)

    box = factories.presentation(session_factory, active.id, "CAJA")
    factories.identifier(session_factory, active.id, "ZZ002", "OTHER")
    gtin = factories.identifier(session_factory, active.id, "7702010000017", presentation_id=box.id)
    factories.identifier(session_factory, active.id, "AA001", "BARCODE")
    factories.identifier(session_factory, active.id, "OLD9", "OTHER", status="INACTIVE")
    with test_engine.begin() as connection:
        connection.execute(text("UPDATE public.global_product_identifiers SET is_primary = true WHERE id = :id"),
                           {"id": str(gtin.id)})
    return {"products": [active.id, inactive.id]}


def test_summary_views_match_batch_lookup(api, catalog, test_engine):
    missing = uuid4()
    ids = [*catalog["products"], missing]
    response = api.post(URL, json={"ids": [str(value) for value in ids]})
    assert response.status_code == 200, response.text
    items = {item["id"]: item for item in response.json()["items"]}

    with test_engine.connect() as connection:
        for product_id in catalog["products"]:
            expected = {key: value for key, value in items[str(product_id)].items() if key not in IMAGE_FIELDS}
            assert _from_views(connection, product_id) == expected, f"producto {product_id}"
        assert _from_views(connection, missing) is None
    assert items[str(missing)]["found"] is False

    active = items[str(catalog["products"][0])]
    assert [c["code"] for c in active["categories"]] == ["HIGIENE", "ALFA", "ZETA"]
    assert [i["value"] for i in active["identifiers"]] == ["7702010000017", "AA001", "ZZ002"]
    assert active["brand"]["code"] == "COLGATE"
    assert items[str(catalog["products"][1])]["brand"] is None


def test_summary_views_have_no_image_columns(test_engine):
    with test_engine.connect() as connection:
        columns = connection.execute(
            text("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'contract' "
                 "AND table_name LIKE 'v1_product_summar%' AND (column_name LIKE '%image%' OR column_name LIKE '%asset%')")
        ).all()
    assert columns == []


# --------------------------------------------------------------------------- roles de lectura (grants.yaml)


def _denied(engine, sql: str) -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text(sql))
    except DBAPIError:
        return True
    return False


def test_piq_reader_reads_summary_views_and_not_public_tables(test_database_url, test_engine):
    testing = pytest.importorskip("sio_contract_read.testing")
    url = testing.provision_reader(test_database_url, GRANTS, "product-inventory-query", secrets.token_urlsafe(24))
    reader = create_engine(url, pool_pre_ping=True)
    try:
        with reader.connect() as connection:
            for view in ("v1_product_summaries", "v1_product_summary_categories", "v1_product_summary_identifiers",
                         "v1_units_of_measure"):
                connection.execute(text(f"SELECT * FROM contract.{view} LIMIT 1")).all()
        for table in ("global_products", "global_brands", "global_product_categories", "global_product_identifiers",
                      "product_assets"):
            assert _denied(reader, f"SELECT 1 FROM public.{table} LIMIT 1"), table
        assert _denied(reader, "SELECT 1 FROM contract.v1_presentations LIMIT 1")
    finally:
        reader.dispose()
