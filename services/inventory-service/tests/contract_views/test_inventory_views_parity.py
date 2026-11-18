"""Paridad y acceso de las vistas de contrato de Inventory (spec 025, T037 y T041).

- ``v1_balances``: misma cantidad y ``balance_sequence`` que ``balances/lookup`` para los productos con saldo
  (incluido un saldo que volvió a 0); un producto sin saldo no tiene fila (el API responde ``0.0000`` y secuencia
  ``0``, y el consumidor hace lo mismo).
- ``v1_operations_by_key`` + ``v1_operation_movements`` (``ORDER BY line_index``): reconstruyen lo mismo que
  ``GET inventory-operations/by-key/{key}`` para entradas, salidas, ajustes y reversiones de entrada y de salida.
  Una clave inexistente o de otra empresa no tiene fila, como el ``404``.
- ``v1_inventory_policies`` (T073): la misma política activa y el mismo ``minimum_stock`` que
  ``inventory-policies/lookup``; un producto sin política activa (inactiva, de otra sucursal o inexistente) no tiene
  fila, como ``policy: null``.
- Con ``contract/grants.yaml``, el rol lector de Sales lee sus tres vistas y no las tablas de ``public``; el de
  Purchase no lee ``v1_balances``; el de PIQ lee ``v1_balances`` y ``v1_inventory_policies`` y nada más; todos en solo
  lectura.
- ``downgrade`` a ``0002`` quita las vistas y el esquema; ``upgrade head`` los repone.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from tests.conftest import line, operation_body, reversal_body, run_alembic
from tests.spec022_support import insert_policy

ENTRIES = "/api/v1/inventory-entries"
OUTPUTS = "/api/v1/inventory-outputs"
GRANTS = Path(__file__).resolve().parents[2] / "contract" / "grants.yaml"

MOVEMENT_FIELDS = (
    "id",
    "line_index",
    "origin_detail_id",
    "company_product_id",
    "movement_type",
    "quantity",
    "unit_cost",
    "movement_value",
    "cost_known",
    "reversed_movement_id",
)


def _text(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    return str(value)


def _from_views(engine, company_id, operation_key) -> dict | None:
    """Reconstruye el cuerpo de ``by-key`` (sin auditoría de origen) solo con las vistas de contrato."""
    with engine.connect() as connection:
        head = connection.execute(
            text("SELECT * FROM contract.v1_operations_by_key WHERE company_id = :c AND operation_key = :k"),
            {"c": company_id, "k": operation_key},
        ).mappings().first()
        if head is None:
            return None
        movements = connection.execute(
            text(
                "SELECT * FROM contract.v1_operation_movements WHERE operation_id = :o AND company_id = :c "
                "ORDER BY line_index"
            ),
            {"o": head["operation_id"], "c": company_id},
        ).mappings().all()
    return {
        "id": str(head["operation_id"]),
        "operation_key": str(head["operation_key"]),
        "operation_type": head["operation_type"],
        "company_id": str(head["company_id"]),
        "branch_id": str(head["branch_id"]),
        "reverses_operation_id": _text(head["reverses_operation_id"]),
        "reversed_by_operation_id": _text(head["reversed_by_operation_id"]),
        "created_at": head["created_at"],
        "status": head["status"],
        "movements": [
            {field: _text(row["movement_id" if field == "id" else field]) for field in MOVEMENT_FIELDS}
            for row in movements
        ],
    }


def _from_api(reader, company_id, operation_key) -> dict | None:
    response = reader.get(f"/api/v1/companies/{company_id}/inventory-operations/by-key/{operation_key}")
    if response.status_code == 404:
        return None
    assert response.status_code == 200, response.text
    body = response.json()
    return {
        **{key: body[key] for key in ("id", "operation_key", "operation_type", "company_id", "branch_id",
                                      "reverses_operation_id", "reversed_by_operation_id")},
        "created_at": datetime.fromisoformat(body["created_at"]),
        "movements": [{field: movement[field] for field in MOVEMENT_FIELDS} for movement in body["movements"]],
    }


def _assert_parity(reader, engine, company_id, operation_key) -> dict:
    api = _from_api(reader, company_id, operation_key)
    view = _from_views(engine, company_id, operation_key)
    assert api is not None and view is not None
    status = view.pop("status")
    assert view == api
    assert status == ("REVERSED" if api["reversed_by_operation_id"] else "APPLIED")
    return view


def test_operations_by_key_match_endpoint(operator, as_user, world, test_engine) -> None:
    p0, p1 = world.products[0], world.products[1]
    entry_body = operation_body(world, line(p0, "10", unit_cost="5"), line(p1, "4", unit_cost="2.5"))
    entry = operator.post(ENTRIES, json=entry_body).json()
    output_body = operation_body(world, line(p1, "1"), line(p0, "3"), origin_type="SALE")
    output = operator.post(OUTPUTS, json=output_body).json()
    output_reversal_body = reversal_body(world)
    assert operator.post(f"{OUTPUTS}/{output['id']}/reversal", json=output_reversal_body).status_code == 201

    other_entry_body = operation_body(world, line(p1, "2", unit_cost="3"))
    other_entry = operator.post(ENTRIES, json=other_entry_body).json()
    entry_reversal_body = reversal_body(world)
    assert operator.post(f"{ENTRIES}/{other_entry['id']}/reversal", json=entry_reversal_body).status_code == 201

    clerk = as_user("operario.dao")
    adjustment_key = str(uuid4())
    response = clerk.post(
        f"/api/v1/companies/{world.company}/inventory-adjustments",
        json={
            "adjustment_key": adjustment_key,
            "branch_id": str(world.branch),
            "company_product_id": str(p0),
            "adjustment_type": "NEGATIVE",
            "quantity": "2",
            "unit_cost": None,
            "reason": "Producto dañado en bodega",
        },
    )
    assert response.status_code == 201, response.text

    keys = {
        "ENTRY": entry_body["operation_key"],
        "OUTPUT": output_body["operation_key"],
        "OUTPUT_REVERSAL": output_reversal_body["operation_key"],
        "ENTRY_REVERSAL": entry_reversal_body["operation_key"],
        "ADJUSTMENT": adjustment_key,
    }
    seen = {kind: _assert_parity(clerk, test_engine, world.company, key) for kind, key in keys.items()}

    assert {kind: view["operation_type"] for kind, view in seen.items()} == {kind: kind for kind in keys}
    # Lo que Sales lee de una salida: costo FIFO por movimiento, en el orden de las líneas.
    sold = seen["OUTPUT"]["movements"]
    assert [m["origin_detail_id"] for m in sold] == [item["origin_detail_id"] for item in output_body["lines"]]
    assert [(m["unit_cost"], m["movement_value"], m["cost_known"]) for m in sold] == [
        ("2.5000", "2.50", True),
        ("5.0000", "15.00", True),
    ]
    assert seen["OUTPUT"]["reversed_by_operation_id"] == seen["OUTPUT_REVERSAL"]["id"]
    assert seen["OUTPUT_REVERSAL"]["reverses_operation_id"] == output["id"]
    assert seen["ENTRY"]["reversed_by_operation_id"] is None


def test_unknown_or_foreign_key_has_no_row(operator, as_user, world, test_engine) -> None:
    body = operation_body(world, line(world.products[0], "1"))
    assert operator.post(ENTRIES, json=body).status_code == 201
    clerk = as_user("operario.dao")

    for company, key in ((world.company, str(uuid4())), (world.other_company, body["operation_key"])):
        assert _from_views(test_engine, company, key) is None
    assert _from_api(clerk, world.company, str(uuid4())) is None
    assert _from_views(test_engine, world.company, body["operation_key"]) is not None


def test_balances_match_lookup_and_missing_product_has_no_row(operator, as_user, world, test_engine) -> None:
    stocked, emptied, never = world.products
    operator.post(ENTRIES, json=operation_body(world, line(stocked, "7", unit_cost="4"), line(emptied, "2")))
    operator.post(OUTPUTS, json=operation_body(world, line(emptied, "2"), origin_type="SALE"))

    response = as_user("operario.dao").post(
        f"/api/v1/companies/{world.company}/branches/{world.branch}/balances/lookup",
        json={"company_product_ids": [str(stocked), str(emptied), str(never)]},
    )
    assert response.status_code == 200
    api = {item["company_product_id"]: (item["quantity"], item["balance_sequence"]) for item in response.json()["items"]}

    with test_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT company_product_id, quantity, balance_sequence FROM contract.v1_balances "
                "WHERE company_id = :c AND branch_id = :b AND company_product_id = ANY(:ids)"
            ),
            {"c": world.company, "b": world.branch, "ids": [stocked, emptied, never]},
        ).all()
    view = {str(row.company_product_id): (str(row.quantity), row.balance_sequence) for row in rows}

    assert set(view) == {str(stocked), str(emptied)}
    assert view == {key: api[key] for key in view}
    assert view[str(emptied)] == ("0.0000", 2)
    # Sin fila → el consumidor devuelve 0, igual que el API.
    assert api[str(never)] == ("0.0000", 0)
    assert Decimal(api[str(never)][0]) == Decimal("0")


def test_policies_match_lookup_and_missing_policy_has_no_row(as_user, world, test_engine) -> None:
    with_policy, inactive, foreign_branch = world.products
    insert_policy(test_engine, world.company, world.branch, with_policy, "5.5")
    insert_policy(test_engine, world.company, world.branch, inactive, "3", active=False)
    insert_policy(test_engine, world.company, world.other_branch, foreign_branch, "7")
    missing = uuid4()
    ids = [with_policy, inactive, foreign_branch, missing]

    response = as_user("operario.dao").post(
        f"/api/v1/companies/{world.company}/branches/{world.branch}/inventory-policies/lookup",
        json={"company_product_ids": [str(value) for value in ids]},
    )
    assert response.status_code == 200, response.text
    api = {
        item["company_product_id"]: item["policy"]["minimum_stock"]
        for item in response.json()["items"]
        if item["policy"] is not None
    }

    with test_engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT company_product_id, minimum_stock FROM contract.v1_inventory_policies "
                "WHERE company_id = :c AND branch_id = :b AND company_product_id = ANY(:ids)"
            ),
            {"c": world.company, "b": world.branch, "ids": ids},
        ).all()
        columns = connection.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'contract' "
                 "AND table_name = 'v1_inventory_policies' ORDER BY ordinal_position")
        ).scalars().all()
    view = {str(row.company_product_id): str(row.minimum_stock) for row in rows}

    assert view == api == {str(with_policy): "5.5000"}
    assert columns == ["company_id", "branch_id", "company_product_id", "minimum_stock"]


# --------------------------------------------------------------------------- roles lectores


def _denied(reader, statement: str) -> bool:
    try:
        with reader.connect() as connection:
            connection.execute(text(statement))
    except DBAPIError as error:
        return "permission denied" in str(error.orig) or "read-only transaction" in str(error.orig)
    return False


@pytest.fixture
def reader_for(test_database_url, migrated_database):
    from sio_contract_read.testing import provision_reader

    engines = []

    def _make(consumer: str):
        url = provision_reader(test_database_url, GRANTS, consumer, secrets.token_urlsafe(24))
        engine = create_engine(url)
        engines.append(engine)
        return engine

    yield _make
    for engine in engines:
        engine.dispose()


def test_sales_reader_reads_views_but_not_tables(operator, world, reader_for) -> None:
    operator.post(ENTRIES, json=operation_body(world, line(world.products[0], "3")))
    sales = reader_for("sales")

    with sales.connect() as connection:
        quantity = connection.execute(
            text("SELECT quantity FROM contract.v1_balances WHERE company_id = :c AND company_product_id = :p"),
            {"c": world.company, "p": world.products[0]},
        ).scalar_one()
        for view in ("v1_operations_by_key", "v1_operation_movements"):
            connection.execute(text(f"SELECT 1 FROM contract.{view} LIMIT 1"))
    assert quantity == Decimal("3.0000")

    for table in ("inventory_balances", "inventory_operations", "inventory_movements", "inventory_cost_layers"):
        assert _denied(sales, f"SELECT 1 FROM public.{table} LIMIT 1"), table
    assert _denied(sales, "CREATE TEMP TABLE intento (id int)")


def test_purchase_reader_cannot_read_balances(reader_for) -> None:
    purchase = reader_for("purchase")
    with purchase.connect() as connection:
        connection.execute(text("SELECT 1 FROM contract.v1_operations_by_key LIMIT 1"))
    assert _denied(purchase, "SELECT 1 FROM contract.v1_balances LIMIT 1")


def test_piq_reader_reads_only_its_views(world, test_engine, reader_for) -> None:
    insert_policy(test_engine, world.company, world.branch, world.products[0], "2")
    piq = reader_for("product-inventory-query")
    with piq.connect() as connection:
        minimum = connection.execute(
            text("SELECT minimum_stock FROM contract.v1_inventory_policies WHERE company_id = :c AND branch_id = :b"
                 " AND company_product_id = :p"),
            {"c": world.company, "b": world.branch, "p": world.products[0]},
        ).scalar_one()
        connection.execute(text("SELECT 1 FROM contract.v1_balances LIMIT 1"))
    assert minimum == Decimal("2.0000")
    assert _denied(piq, "SELECT 1 FROM public.inventory_policies LIMIT 1")
    assert _denied(piq, "SELECT 1 FROM contract.v1_operations_by_key LIMIT 1")


# --------------------------------------------------------------------------- migración


def test_downgrade_removes_views_and_upgrade_restores_them(test_database_url, test_engine) -> None:
    def contract_views() -> list[str]:
        with test_engine.connect() as connection:
            return connection.execute(
                text("SELECT table_name FROM information_schema.views WHERE table_schema = 'contract' ORDER BY 1")
            ).scalars().all()

    run_alembic(test_database_url, "downgrade", "0002")
    try:
        assert contract_views() == []
        with test_engine.connect() as connection:
            assert connection.execute(text("SELECT 1 FROM pg_namespace WHERE nspname = 'contract'")).first() is None
    finally:
        run_alembic(test_database_url, "upgrade", "head")
    assert contract_views() == ["v1_balances", "v1_inventory_policies", "v1_operation_movements", "v1_operations_by_key"]
