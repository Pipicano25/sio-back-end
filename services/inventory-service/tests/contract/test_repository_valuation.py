"""Motor valorizado: capas, consumos y saldo en la misma transacción (R-02, R-03; puntos 3 y 6; T011)."""

from __future__ import annotations

from decimal import Decimal as D
from uuid import uuid4

import pytest
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from inventory_service.infrastructure import valuation_repository
from inventory_service.infrastructure.repository import (
    NewLine,
    NewOperation,
    SqlInventoryRepository,
    ValuationInvariantError,
)
from tests.contract.db_rows import insert_layer

TYPES = {
    "ENTRY": ("PURCHASE", "PURCHASE_ENTRY"),
    "OUTPUT": ("SALE", "SALE_OUTPUT"),
}


def op(company, branch, lines, *, operation_type="ENTRY", origin_type=None, currency="COP", key=None) -> NewOperation:
    """`lines`: (producto, cantidad, costo) o (producto, cantidad, costo, tipo de movimiento)."""
    default_origin, default_movement = TYPES.get(operation_type, ("ADJUSTMENT", None))
    return NewOperation(
        operation_key=key or uuid4(),
        client_id="inventory-test-operator",
        created_by="sub-sa-inventory-test-operator",
        operation_type=operation_type,
        company_id=company,
        branch_id=branch,
        origin_type=origin_type or default_origin,
        origin_id=uuid4(),
        application_user_id=uuid4(),
        correlation_id=uuid4(),
        reason="Ajuste ficticio" if operation_type == "ADJUSTMENT" else None,
        reverses_operation_id=None,
        request_hash="c" * 64,
        currency_code=currency,
        lines=[
            NewLine(
                index=i,
                origin_detail_id=uuid4(),
                company_product_id=item[0],
                quantity=D(str(item[1])),
                unit_cost=D(str(item[2])) if item[2] is not None else None,
                movement_type=item[3] if len(item) > 3 else default_movement,
            )
            for i, item in enumerate(lines)
        ],
    )


@pytest.fixture
def repo(test_engine, clean_database):
    sessions = []

    def make() -> SqlInventoryRepository:
        session = Session(test_engine, expire_on_commit=False)
        sessions.append(session)
        return SqlInventoryRepository(session, lock_timeout_ms=5000)

    yield make
    for session in sessions:
        session.close()


def rows(test_engine, sql: str, **params):
    with test_engine.connect() as connection:
        return connection.execute(text(sql), params).all()


def snapshot(test_engine) -> dict:
    return {
        table: rows(test_engine, f"SELECT * FROM {table} ORDER BY 1")
        for table in (
            "inventory_operations",
            "inventory_movements",
            "inventory_balances",
            "inventory_cost_layers",
            "inventory_cost_consumptions",
        )
    }


def test_entry_creates_a_valued_layer_and_movement(repo, test_engine) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    operation = op(company, branch, [(product, 10, 1000)])
    stored = repo().apply_operation(operation)
    movement = stored.movements[0]
    assert (movement.unit_cost, movement.movement_value, movement.cost_known) == (D("1000"), D("10000.00"), True)

    layer = rows(test_engine, "SELECT * FROM inventory_cost_layers")[0]
    assert (layer.layer_kind, layer.origin_movement_id, layer.original_quantity, layer.remaining_quantity) == (
        "ENTRY",
        movement.id,
        D("10"),
        D("10"),
    )
    assert (layer.unit_cost, layer.cost_known, layer.currency_code, layer.status) == (D("1000"), True, "COP", "OPEN")
    assert (layer.origin_purchase_id, layer.origin_purchase_detail_id) == (operation.origin_id, operation.lines[0].origin_detail_id)

    balance = rows(test_engine, "SELECT * FROM inventory_balances")[0]
    assert (balance.quantity, balance.inventory_value, balance.average_unit_cost, balance.has_unknown_cost) == (
        D("10"),
        D("10000.00"),
        D("1000.0000"),
        False,
    )
    assert stored.valuation_after[product].inventory_value == D("10000.00")


def test_output_consumes_fifo_inside_the_same_transaction(repo, test_engine) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    repo().apply_operation(op(company, branch, [(product, 10, 1000), (product, 5, 1300)]))
    stored = repo().apply_operation(op(company, branch, [(product, 12, None)], operation_type="OUTPUT"))

    movement = stored.movements[0]
    assert (movement.unit_cost, movement.movement_value, movement.cost_known) == (D("1050.0000"), D("12600.00"), True)
    consumed = rows(
        test_engine,
        "SELECT c.consumption_type, c.quantity, c.unit_cost, c.cost_amount, c.cost_known FROM inventory_cost_consumptions c "
        "JOIN inventory_cost_layers l ON l.id = c.cost_layer_id WHERE c.movement_id = :m ORDER BY l.received_at, l.id",
        m=movement.id,
    )
    assert [tuple(row) for row in consumed] == [
        ("CONSUME", D("10"), D("1000"), D("10000.00"), True),
        ("CONSUME", D("2"), D("1300"), D("2600.00"), True),
    ]
    layers = rows(test_engine, "SELECT remaining_quantity, status FROM inventory_cost_layers ORDER BY received_at, id")
    assert [tuple(row) for row in layers] == [(D("0"), "CLOSED"), (D("3"), "OPEN")]
    balance = rows(test_engine, "SELECT quantity, inventory_value, average_unit_cost FROM inventory_balances")[0]
    assert tuple(balance) == (D("3"), D("3900.00"), D("1300.0000"))


def test_layers_of_one_operation_keep_the_line_order(repo, test_engine) -> None:
    """Capas creadas en la misma operación: el orden FIFO respeta el orden de las líneas."""
    company, branch, product = uuid4(), uuid4(), uuid4()
    repo().apply_operation(op(company, branch, [(product, 1, c) for c in (10, 20, 30, 40, 50)]))
    stored = repo().apply_operation(op(company, branch, [(product, 2, None)], operation_type="OUTPUT"))
    assert stored.movements[0].movement_value == D("30.00")  # 10 + 20


def test_each_line_brings_its_movement_type(repo, test_engine) -> None:
    company, branch, a, b = uuid4(), uuid4(), uuid4(), uuid4()
    repo().apply_operation(op(company, branch, [(a, 10, 100), (b, 10, 200)]))
    stored = repo().apply_operation(
        op(
            company,
            branch,
            [(a, 2, None, "NEGATIVE_ADJUSTMENT"), (b, 3, 250, "POSITIVE_ADJUSTMENT")],
            operation_type="ADJUSTMENT",
            origin_type="COUNT",
        )
    )
    assert [(m.movement_type, m.new_balance, m.movement_value) for m in stored.movements] == [
        ("NEGATIVE_ADJUSTMENT", D("8"), D("200.00")),
        ("POSITIVE_ADJUSTMENT", D("13"), D("750.00")),
    ]
    kinds = rows(test_engine, "SELECT layer_kind, unit_cost FROM inventory_cost_layers WHERE company_product_id = :b ORDER BY received_at, id", b=b)
    assert [tuple(row) for row in kinds] == [("ENTRY", D("200")), ("ADJUSTMENT", D("250"))]


def test_failure_after_consumptions_rolls_everything_back(repo, test_engine) -> None:
    """Punto 3: un fallo después de consumir no deja consumos parciales ni capas inconsistentes."""
    company, branch, product = uuid4(), uuid4(), uuid4()
    repo().apply_operation(op(company, branch, [(product, 10, 1000), (product, 5, 1300)]))
    before = snapshot(test_engine)

    def explode(session, stored):
        # Los consumos ya están escritos en esta transacción cuando corre el gancho.
        assert session.execute(text("SELECT count(*) FROM inventory_cost_consumptions")).scalar_one() == 2
        raise RuntimeError("falla inyectada después de consumir")

    with pytest.raises(RuntimeError, match="falla inyectada"):
        repo().apply_operation(op(company, branch, [(product, 12, None)], operation_type="OUTPUT"), explode)

    assert snapshot(test_engine) == before
    stored = repo().apply_operation(op(company, branch, [(product, 1, None)], operation_type="OUTPUT"))
    assert stored.movements[0].balance_sequence == 3  # sin huecos


def test_balances_are_locked_before_layers_in_a_deterministic_order(repo, test_engine) -> None:
    company, branch = uuid4(), uuid4()
    products = sorted((uuid4() for _ in range(3)), key=str)
    repo().apply_operation(op(company, branch, [(p, 5, 10) for p in products] + [(p, 5, 20) for p in products]))

    statements: list[str] = []

    def capture(conn, cursor, statement, parameters, context, executemany):
        if "FOR UPDATE" in statement:
            statements.append(" ".join(statement.split()))

    event.listen(test_engine, "before_cursor_execute", capture)
    try:
        # Líneas en orden inverso: los bloqueos siguen el orden global.
        repo().apply_operation(op(company, branch, [(p, 7, None) for p in reversed(products)], operation_type="OUTPUT"))
    finally:
        event.remove(test_engine, "before_cursor_execute", capture)

    assert len(statements) == 2
    assert "FROM inventory_balances" in statements[0]
    assert "ORDER BY inventory_balances.company_product_id" in statements[0]
    assert "FROM inventory_cost_layers" in statements[1]
    assert (
        "ORDER BY inventory_cost_layers.company_product_id, inventory_cost_layers.received_at, inventory_cost_layers.id"
        in statements[1]
    )


def test_invariant_violation_rolls_back(repo, test_engine, monkeypatch) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    repo().apply_operation(op(company, branch, [(product, 10, 1000)]))
    before = snapshot(test_engine)
    original = valuation_repository.consume

    def leaky(layers, quantity):
        takes = original(layers, quantity)
        layers[0].remaining += D("0.0001")  # una capa queda con más de lo que dice el saldo
        return takes

    monkeypatch.setattr(valuation_repository, "consume", leaky)
    with pytest.raises(ValuationInvariantError):
        repo().apply_operation(op(company, branch, [(product, 3, None)], operation_type="OUTPUT"))
    assert snapshot(test_engine) == before


def test_unknown_cost_propagates_to_consumptions_movements_and_balance(repo, test_engine) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    with test_engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO inventory_balances (company_id, branch_id, company_product_id, quantity, version, "
                "inventory_value, average_unit_cost, has_unknown_cost, created_by, updated_by) "
                "VALUES (:c, :b, :p, 5, 0, 0, 0, true, 's', 's')"
            ),
            {"c": company, "b": branch, "p": product},
        )
        insert_layer(
            connection, company_id=company, branch_id=branch, company_product_id=product, original_quantity=5,
            remaining_quantity=5, unit_cost=0, cost_known=False, currency_code=None,
        )

    first = repo().apply_operation(op(company, branch, [(product, 2, None)], operation_type="OUTPUT"))
    assert (first.movements[0].unit_cost, first.movements[0].movement_value, first.movements[0].cost_known) == (
        D("0.0000"),
        D("0.00"),
        False,
    )
    assert rows(test_engine, "SELECT cost_known FROM inventory_cost_consumptions")[0].cost_known is False
    assert first.valuation_after[product].has_unknown_cost is True

    second = repo().apply_operation(op(company, branch, [(product, 3, 10)]))
    assert second.valuation_after[product].has_unknown_cost is True  # la apertura conserva 3 sin costo
    assert second.valuation_after[product].inventory_value == D("30.00")

    third = repo().apply_operation(op(company, branch, [(product, 4, None)], operation_type="OUTPUT"))
    # Consume 3 de la apertura (sin costo) y 1 de la entrada: el movimiento queda con costo desconocido.
    assert third.movements[0].cost_known is False
    assert third.movements[0].movement_value == D("10.00")
    assert third.valuation_after[product].has_unknown_cost is False
    balance = rows(test_engine, "SELECT quantity, inventory_value, has_unknown_cost FROM inventory_balances")[0]
    assert tuple(balance) == (D("2"), D("20.00"), False)


def test_replay_rebuilds_the_valuation_of_that_moment(repo) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    first = op(company, branch, [(product, 10, 1000)])
    repo().apply_operation(first)
    repo().apply_operation(op(company, branch, [(product, 4, None)], operation_type="OUTPUT"))
    found = repo().find_by_key(first.operation_key)
    valuation = found.valuation_after[product]
    assert (valuation.inventory_value, valuation.average_unit_cost, valuation.has_unknown_cost) == (
        D("10000.00"),
        D("1000.0000"),
        False,
    )
