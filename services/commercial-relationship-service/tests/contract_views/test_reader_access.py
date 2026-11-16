"""Roles de lectura de ``contract/grants.yaml`` sobre las vistas de Commercial Relationship (spec 025, T039).

Aplica en la base de pruebas los permisos declarados para un consumidor con ``provision_reader`` (lo mismo que hace
``infrastructure/scripts/contract-readers/provision.py``) y comprueba, conectado como su rol de lectura, que:

- lee cada vista declarada;
- no lee tablas de ``public`` ni vistas no declaradas (``permission denied``);
- no escribe (transacción de solo lectura).
"""

from __future__ import annotations

import secrets
from pathlib import Path

import pytest
from sio_contract_read import provisioning as prov
from sio_contract_read.testing import provision_reader
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

GRANTS = Path(__file__).resolve().parents[2] / "contract" / "grants.yaml"
CR_VIEWS = {"v1_company_products", "v1_company_product_presentations", "v1_company_customers", "v1_price_lists"}


def _reader(test_database_url: str, consumer: str):
    url = provision_reader(test_database_url, GRANTS, consumer, secrets.token_urlsafe(24))
    return create_engine(url, pool_pre_ping=True)


def _denied(engine, sql: str) -> str:
    with engine.connect() as connection, pytest.raises(DBAPIError) as error:
        connection.execute(text(sql))
    return str(error.value.orig)


def test_grants_declare_only_existing_views(test_engine) -> None:
    grants = prov.load_grants(GRANTS)
    assert grants.owner == "commercial-relationship" and grants.abbreviation == "cr"
    declared = {view for consumer in grants.consumers for view in consumer.views}
    with test_engine.connect() as connection:
        existing = set(connection.execute(
            text("SELECT table_name FROM information_schema.views WHERE table_schema = 'contract'")
        ).scalars())
    assert declared <= existing
    assert existing == CR_VIEWS
    by_consumer = {consumer.service: set(consumer.views) for consumer in grants.consumers}
    assert by_consumer == {
        "sales": CR_VIEWS,
        "purchase": {"v1_company_products", "v1_company_product_presentations"},
        "inventory": {"v1_company_products"},
        "product-inventory-query": {"v1_company_products", "v1_company_product_presentations"},
    }


def test_sales_reader_reads_views_and_nothing_else(test_database_url, migrated_database) -> None:
    engine = _reader(test_database_url, "sales")
    try:
        with engine.connect() as connection:
            for view in sorted(CR_VIEWS):
                connection.execute(text(f"SELECT * FROM contract.{view} LIMIT 1")).all()
        for table in ("company_products", "company_customers", "price_lists", "price_list_items"):
            assert "permission denied" in _denied(engine, f"SELECT 1 FROM public.{table} LIMIT 1"), table
        assert "read-only" in _denied(engine, "CREATE TEMP TABLE probe (id int)")
    finally:
        engine.dispose()


def test_inventory_reader_cannot_read_undeclared_views(test_database_url, migrated_database) -> None:
    engine = _reader(test_database_url, "inventory")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT * FROM contract.v1_company_products LIMIT 1")).all()
        for view in sorted(CR_VIEWS - {"v1_company_products"}):
            assert "permission denied" in _denied(engine, f"SELECT 1 FROM contract.{view} LIMIT 1"), view
    finally:
        engine.dispose()
