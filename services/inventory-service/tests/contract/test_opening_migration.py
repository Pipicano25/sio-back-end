"""Capa de apertura de la migración `0002` (FR-057, R-05, punto 2 de la aprobación del plan; T007).

Cada prueba usa un esquema temporal: se migra a `0001`, se siembran datos como los
dejaba la Fase A y se aplica `0002`.
"""

from __future__ import annotations

import importlib.util
from decimal import Decimal as D
from pathlib import Path
from uuid import UUID

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import PROJECT_ROOT, run_alembic
from tests.contract.fase_a_seed import FaseASeeder

COMPANY = UUID("11111111-0000-4000-8000-000000000001")
BRANCH = UUID("22222222-0000-4000-8000-000000000002")
P_COSTED = UUID("33333333-0000-4000-8000-000000000001")  # 10 a 1000, 5 a 1300, salida 3 → 12 a 1300
P_REVERSED = UUID("33333333-0000-4000-8000-000000000002")  # 10 a 500, 4 a 900 revertida → 10 a 500
P_NO_COST = UUID("33333333-0000-4000-8000-000000000003")  # 7 sin costo → 0 "sin costo"
P_ZERO = UUID("33333333-0000-4000-8000-000000000004")  # 5 a 100, salida 5 → sin apertura
P_LAST_NO_COST = UUID("33333333-0000-4000-8000-000000000005")  # 3 a 200 y 2 sin costo → 5 a 200


def load_migration():
    path = Path(PROJECT_ROOT) / "alembic" / "versions" / "0002_inventory_complementary.py"
    spec = importlib.util.spec_from_file_location("migration_0002", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def schema_url(base_url: str, schema: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}options=-csearch_path%3D{schema}"


@pytest.fixture
def scratch(test_database_url):
    """Fábrica de esquemas temporales migrados a `0001`."""
    created: list[str] = []
    admin = create_engine(test_database_url)

    def make(name: str) -> str:
        with admin.begin() as connection:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {name} CASCADE"))
            connection.execute(text(f"CREATE SCHEMA {name}"))
        created.append(name)
        url = schema_url(test_database_url, name)
        run_alembic(url, "upgrade", "0001")
        return url

    yield make
    with admin.begin() as connection:
        for name in created:
            connection.execute(text(f"DROP SCHEMA IF EXISTS {name} CASCADE"))
    admin.dispose()


def seed(url: str) -> None:
    engine = create_engine(url)
    with engine.begin() as connection:
        s = FaseASeeder(connection, COMPANY, BRANCH)
        s.entry(P_COSTED, 10, 1000)
        s.entry(P_COSTED, 5, 1300)
        s.output(P_COSTED, 3)
        s.entry(P_REVERSED, 10, 500)
        reversed_entry = s.entry(P_REVERSED, 4, 900)
        s.reverse_entry(P_REVERSED, reversed_entry, 4, 900)
        s.entry(P_NO_COST, 7)
        s.entry(P_ZERO, 5, 100)
        s.output(P_ZERO, 5)
        s.entry(P_LAST_NO_COST, 3, 200)
        s.entry(P_LAST_NO_COST, 2)
        s.flush_balances()
    engine.dispose()


def layers(url: str) -> dict[UUID, list]:
    engine = create_engine(url)
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT company_product_id, layer_kind, original_quantity, remaining_quantity, unit_cost, cost_known, "
                "currency_code, status, origin_movement_id FROM inventory_cost_layers ORDER BY company_product_id"
            )
        ).all()
    engine.dispose()
    result: dict[UUID, list] = {}
    for row in rows:
        result.setdefault(row.company_product_id, []).append(row)
    return result


def balances(url: str) -> dict[UUID, tuple]:
    engine = create_engine(url)
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT company_product_id, quantity, inventory_value, average_unit_cost, has_unknown_cost "
                "FROM inventory_balances"
            )
        ).all()
    engine.dispose()
    return {row.company_product_id: tuple(row[1:]) for row in rows}


def test_one_opening_layer_per_balance_with_the_exact_quantity_and_cost(scratch) -> None:
    url = scratch("opening_a")
    seed(url)
    run_alembic(url, "upgrade", "head")

    found = layers(url)
    assert set(found) == {P_COSTED, P_REVERSED, P_NO_COST, P_LAST_NO_COST}  # P_ZERO (saldo 0) sin apertura
    assert all(len(items) == 1 for items in found.values())
    for items in found.values():
        layer = items[0]
        assert (layer.layer_kind, layer.status, layer.origin_movement_id, layer.currency_code) == (
            "OPENING",
            "OPEN",
            None,
            None,
        )
        assert layer.original_quantity == layer.remaining_quantity

    expected = {
        P_COSTED: (D("12"), D("1300"), True),
        P_REVERSED: (D("10"), D("500"), True),  # la entrada de 900 fue revertida
        P_NO_COST: (D("7"), D("0"), False),
        P_LAST_NO_COST: (D("5"), D("200"), True),  # la última entrada no tenía costo: se toma la anterior con costo
    }
    for product, (quantity, cost, known) in expected.items():
        layer = found[product][0]
        assert (layer.remaining_quantity, layer.unit_cost, layer.cost_known) == (quantity, cost, known), product

    saldo = balances(url)
    assert saldo[P_COSTED] == (D("12"), D("15600.00"), D("1300.0000"), False)
    assert saldo[P_REVERSED] == (D("10"), D("5000.00"), D("500.0000"), False)
    assert saldo[P_NO_COST] == (D("7"), D("0.00"), D("0.0000"), True)
    assert saldo[P_ZERO] == (D("0"), D("0.00"), None, False)
    # Σ capas abiertas = saldo, exacto, para cada saldo.
    for product, (quantity, *_rest) in saldo.items():
        assert sum((layer.remaining_quantity for layer in found.get(product, []) if layer.status == "OPEN"), D(0)) == quantity


def test_opening_is_deterministic(scratch) -> None:
    first, second = scratch("opening_b1"), scratch("opening_b2")
    for url in (first, second):
        seed(url)
        run_alembic(url, "upgrade", "head")

    def summary(url):
        return {
            product: [(row.original_quantity, row.unit_cost, row.cost_known) for row in items]
            for product, items in layers(url).items()
        }

    assert summary(first) == summary(second)
    assert balances(first) == balances(second)


def test_opening_step_cannot_create_duplicates(scratch) -> None:
    url = scratch("opening_c")
    seed(url)
    run_alembic(url, "upgrade", "head")
    migration = load_migration()
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            assert migration.create_opening_layers(connection) == 0
            migration.verify_opening_layers(connection)
        assert {product: len(items) for product, items in layers(url).items()} == {
            P_COSTED: 1,
            P_REVERSED: 1,
            P_NO_COST: 1,
            P_LAST_NO_COST: 1,
        }
        with pytest.raises(IntegrityError) as error, engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO inventory_cost_layers (company_id, branch_id, company_product_id, layer_kind, "
                    "original_quantity, remaining_quantity, unit_cost, cost_known, received_at, status, "
                    "created_by, updated_by) VALUES (:c, :b, :p, 'OPENING', 1, 1, 0, false, now(), 'OPEN', 's', 's')"
                ),
                {"c": COMPANY, "b": BRANCH, "p": P_COSTED},
            )
        assert "uq_inventory_cost_layers_opening" in str(error.value)
    finally:
        engine.dispose()


def test_verification_detects_a_mismatch(scratch) -> None:
    url = scratch("opening_d")
    seed(url)
    run_alembic(url, "upgrade", "head")
    migration = load_migration()
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            connection.execute(
                text("UPDATE inventory_cost_layers SET remaining_quantity = remaining_quantity - 1 WHERE company_product_id = :p"),
                {"p": P_COSTED},
            )
            with pytest.raises(migration.OpeningLayersMismatch):
                migration.verify_opening_layers(connection)
            transaction.rollback()
    finally:
        engine.dispose()


def test_upgrade_aborts_and_rolls_back_when_layers_do_not_match_balances(scratch, monkeypatch) -> None:
    """Punto 5: si tras el backfill capas ≠ saldo, `0002` aborta y la base queda en `0001`."""
    url = scratch("opening_e")
    seed(url)
    migration = load_migration()
    original = migration.create_opening_layers

    def broken(connection) -> int:
        created = original(connection)
        connection.execute(
            text("UPDATE inventory_cost_layers SET remaining_quantity = remaining_quantity - 0.0001, "
                 "original_quantity = original_quantity - 0.0001 WHERE company_product_id = :p"),
            {"p": P_NO_COST},
        )
        return created

    monkeypatch.setattr(migration, "create_opening_layers", broken)
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            context = MigrationContext.configure(connection)
            with Operations.context(context), pytest.raises(migration.OpeningLayersMismatch):
                migration.upgrade()
            transaction.rollback()

        with engine.connect() as connection:
            tables = {row[0] for row in connection.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'opening_e'"))}
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert "inventory_cost_layers" not in tables
        assert version == "0001"
    finally:
        engine.dispose()
