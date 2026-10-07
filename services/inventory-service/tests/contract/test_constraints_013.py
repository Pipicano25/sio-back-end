"""Restricciones nuevas de `data-model.md` (013): cada `CHECK`/`UNIQUE` rechaza un `INSERT` inválido (T008)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.contract.db_rows import (
    insert_adjustment,
    insert_balance,
    insert_company_policy,
    insert_consumption,
    insert_count,
    insert_count_detail,
    insert_layer,
    insert_movement,
    insert_operation,
    insert_policy,
)

NOW = datetime(2026, 10, 6, tzinfo=UTC)


@pytest.fixture
def conn(test_engine, clean_database):
    with test_engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()


def _rejects(conn, constraint: str | tuple[str, ...], action) -> None:
    savepoint = conn.begin_nested()
    with pytest.raises(IntegrityError) as error:
        action()
    savepoint.rollback()
    names = (constraint,) if isinstance(constraint, str) else constraint
    assert any(f'"{name}"' in str(error.value) for name in names), str(error.value)[:300]


# inventory_operations / inventory_movements / inventory_balances --------------------


def test_operations_accept_adjustments_with_their_origins_and_line_limits(conn) -> None:
    insert_operation(conn, operation_type="ADJUSTMENT", origin_type="ADJUSTMENT")
    insert_operation(conn, operation_type="ADJUSTMENT", origin_type="COUNT", line_count=1000)
    _rejects(conn, "ck_inventory_operations_origin_type", lambda: insert_operation(conn, operation_type="ADJUSTMENT", origin_type="PURCHASE"))
    _rejects(conn, "ck_inventory_operations_origin_type", lambda: insert_operation(conn, operation_type="ENTRY", origin_type="COUNT"))
    _rejects(conn, "ck_inventory_operations_line_count", lambda: insert_operation(conn, operation_type="ADJUSTMENT", origin_type="COUNT", line_count=1001))
    _rejects(conn, "ck_inventory_operations_line_count", lambda: insert_operation(conn, operation_type="ADJUSTMENT", origin_type="ADJUSTMENT", line_count=101))
    _rejects(conn, "ck_inventory_operations_line_count", lambda: insert_operation(conn, line_count=101))


def test_adjustment_movement_types_and_math(conn) -> None:
    op = insert_operation(conn, operation_type="ADJUSTMENT", origin_type="ADJUSTMENT")
    insert_movement(conn, op, movement_type="POSITIVE_ADJUSTMENT", origin_type="ADJUSTMENT", previous_balance=5, new_balance=15)
    insert_movement(conn, op, line_index=1, movement_type="NEGATIVE_ADJUSTMENT", origin_type="ADJUSTMENT", previous_balance=15, new_balance=5)
    _rejects(conn, "ck_inventory_movements_balance_math", lambda: insert_movement(conn, op, line_index=2, movement_type="POSITIVE_ADJUSTMENT", previous_balance=15, new_balance=5))
    _rejects(conn, "ck_inventory_movements_balance_math", lambda: insert_movement(conn, op, line_index=2, movement_type="NEGATIVE_ADJUSTMENT", previous_balance=5, new_balance=15))


def test_new_movements_must_be_valued(conn) -> None:
    """Punto 6: `ck_inventory_movements_valued` rechaza toda fila nueva sin costo, valor o `cost_known`."""
    op = insert_operation(conn)
    _rejects(conn, "ck_inventory_movements_valued", lambda: insert_movement(conn, op, unit_cost=None))
    _rejects(conn, "ck_inventory_movements_valued", lambda: insert_movement(conn, op, movement_value=None))
    _rejects(conn, "ck_inventory_movements_valued", lambda: insert_movement(conn, op, cost_known=None))
    _rejects(conn, "ck_inventory_movements_valued", lambda: insert_movement(conn, op, valued=False))
    _rejects(conn, "ck_inventory_movements_movement_value_non_negative", lambda: insert_movement(conn, op, movement_value=-1))


def test_balance_inventory_value_non_negative(conn) -> None:
    balance = insert_balance(conn, quantity=1, version=1)
    _rejects(
        conn,
        "ck_inventory_balances_inventory_value_non_negative",
        lambda: conn.execute(text("UPDATE inventory_balances SET inventory_value = -1 WHERE id = :id"), {"id": balance}),
    )


# company_inventory_policies -----------------------------------------------------


def test_company_policy_rules(conn) -> None:
    company = uuid4()
    insert_company_policy(conn, company_id=company)
    _rejects(conn, "uq_company_inventory_policies_company", lambda: insert_company_policy(conn, company_id=company))
    _rejects(conn, "ck_company_inventory_policies_system", lambda: insert_company_policy(conn, inventory_system="OTRO"))
    _rejects(conn, "ck_company_inventory_policies_valuation_fifo", lambda: insert_company_policy(conn, valuation_method="WEIGHTED_AVERAGE"))
    _rejects(conn, "ck_company_inventory_policies_replenishment", lambda: insert_company_policy(conn, replenishment_strategy="OTRA"))
    insert_company_policy(conn, inventory_system="PERIODIC", replenishment_strategy="JIT")


# inventory_policies ------------------------------------------------------------


def test_product_policy_rules(conn) -> None:
    _rejects(conn, "ck_inventory_policies_levels", lambda: insert_policy(conn, minimum_stock=-1))
    _rejects(conn, "ck_inventory_policies_levels", lambda: insert_policy(conn, minimum_stock=10, target_stock=5))
    insert_policy(conn, target_stock=None)
    _rejects(conn, "ck_inventory_policies_service_level", lambda: insert_policy(conn, service_level=0))
    _rejects(conn, "ck_inventory_policies_service_level", lambda: insert_policy(conn, service_level=1))
    insert_policy(conn, service_level=None)
    _rejects(conn, "ck_inventory_policies_window", lambda: insert_policy(conn, calculation_window_days=0))
    _rejects(conn, "ck_inventory_policies_window", lambda: insert_policy(conn, calculation_window_days=3651))
    _rejects(conn, "ck_inventory_policies_safety_method", lambda: insert_policy(conn, safety_stock_method="OTRO"))
    _rejects(conn, "ck_inventory_policies_mode", lambda: insert_policy(conn, replenishment_mode="AUTO"))


def test_only_one_active_product_policy(conn) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    insert_policy(conn, company_id=company, branch_id=branch, company_product_id=product)
    _rejects(
        conn,
        "uq_inventory_policies_active",
        lambda: insert_policy(conn, company_id=company, branch_id=branch, company_product_id=product),
    )
    insert_policy(conn, company_id=company, branch_id=branch, company_product_id=product, is_active=False)


# inventory_adjustments ---------------------------------------------------------


def _adjustment_movement(conn, **movement):
    op = insert_operation(conn, operation_type="ADJUSTMENT", origin_type="ADJUSTMENT")
    values = {
        "movement_type": "NEGATIVE_ADJUSTMENT",
        "origin_type": "ADJUSTMENT",
        "previous_balance": 10,
        "new_balance": 7,
        "quantity": 3,
    }
    values.update(movement)
    return op, insert_movement(conn, op, **values)


@pytest.mark.parametrize(
    ("overrides", "constraint"),
    [
        ({"adjustment_type": "OTRO"}, ("ck_inventory_adjustments_type", "ck_inventory_adjustments_balance_math")),
        ({"quantity": 0, "new_balance": 10}, ("ck_inventory_adjustments_quantity_positive", "ck_inventory_adjustments_balance_math")),
        ({"reason": "  "}, "ck_inventory_adjustments_reason"),
        ({"reason": " con espacios "}, "ck_inventory_adjustments_reason"),
        ({"reason": "x" * 2001}, "ck_inventory_adjustments_reason"),
        ({"new_balance": 8}, "ck_inventory_adjustments_balance_math"),
        ({"adjustment_type": "POSITIVE"}, "ck_inventory_adjustments_balance_math"),
        ({"previous_balance": 2, "new_balance": -1}, "ck_inventory_adjustments_balance_math"),
        ({"unit_cost": -1}, "ck_inventory_adjustments_values_non_negative"),
        ({"adjustment_value": -1}, "ck_inventory_adjustments_values_non_negative"),
        ({"updated_by": "otro"}, "ck_inventory_adjustments_audit_unchanged"),
    ],
)
def test_adjustment_rules(conn, overrides, constraint) -> None:
    op, movement = _adjustment_movement(conn)
    _rejects(conn, constraint, lambda: insert_adjustment(conn, op, movement, **overrides))


def test_valid_adjustments_and_unique_movement(conn) -> None:
    op, movement = _adjustment_movement(conn)
    insert_adjustment(conn, op, movement)
    _rejects(conn, "uq_inventory_adjustments_movement", lambda: insert_adjustment(conn, op, movement))
    positive_op, positive = _adjustment_movement(conn, movement_type="POSITIVE_ADJUSTMENT", previous_balance=7, new_balance=10)
    insert_adjustment(conn, positive_op, positive, adjustment_type="POSITIVE", previous_balance=7, new_balance=10)


# inventory_counts y detalles -----------------------------------------------------


def test_count_status_and_lifecycle(conn) -> None:
    insert_count(conn)
    insert_count(conn, status="IN_PROGRESS", started_at=NOW)
    insert_count(conn, status="CANCELLED", cancelled_by_user_id=uuid4(), cancelled_at=NOW, cancel_reason="Error de planeación")
    _rejects(conn, ("ck_inventory_counts_status", "ck_inventory_counts_lifecycle"), lambda: insert_count(conn, status="OTRO"))
    _rejects(conn, "ck_inventory_counts_lifecycle", lambda: insert_count(conn, started_at=NOW))
    _rejects(conn, "ck_inventory_counts_lifecycle", lambda: insert_count(conn, status="IN_PROGRESS"))
    _rejects(conn, "ck_inventory_counts_lifecycle", lambda: insert_count(conn, status="COMPLETED", started_at=NOW))
    _rejects(conn, "ck_inventory_counts_lifecycle", lambda: insert_count(conn, status="CANCELLED", cancelled_at=NOW))


def test_only_one_count_in_progress_per_branch(conn) -> None:
    company, branch = uuid4(), uuid4()
    insert_count(conn, company_id=company, branch_id=branch, status="IN_PROGRESS", started_at=NOW)
    insert_count(conn, company_id=company, branch_id=branch)  # un DRAFT no cuenta
    _rejects(
        conn,
        "uq_inventory_counts_in_progress",
        lambda: insert_count(conn, company_id=company, branch_id=branch, status="IN_PROGRESS", started_at=NOW),
    )


def test_count_detail_rules(conn) -> None:
    count = insert_count(conn)
    product = uuid4()
    insert_count_detail(conn, count, company_product_id=product)
    _rejects(conn, "uq_inventory_count_details_product", lambda: insert_count_detail(conn, count, company_product_id=product))
    _rejects(conn, "ck_inventory_count_details_quantities", lambda: insert_count_detail(conn, count, counted_quantity=-1, difference_quantity=-11))
    _rejects(conn, "ck_inventory_count_details_quantities", lambda: insert_count_detail(conn, count, unit_cost=-1))
    _rejects(conn, "ck_inventory_count_details_difference", lambda: insert_count_detail(conn, count, difference_quantity=2))


# inventory_cost_layers --------------------------------------------------------


def test_layer_rules(conn) -> None:
    op = insert_operation(conn)
    movement = insert_movement(conn, op)
    insert_layer(conn, layer_kind="ENTRY", origin_movement_id=movement)
    _rejects(conn, "uq_inventory_cost_layers_origin_movement", lambda: insert_layer(conn, layer_kind="ENTRY", origin_movement_id=movement))
    _rejects(conn, "ck_inventory_cost_layers_kind", lambda: insert_layer(conn, layer_kind="OTRA"))
    _rejects(conn, "ck_inventory_cost_layers_origin", lambda: insert_layer(conn, layer_kind="ENTRY"))
    _rejects(conn, "ck_inventory_cost_layers_origin", lambda: insert_layer(conn, origin_movement_id=insert_movement(conn, op, line_index=1)))
    _rejects(conn, ("ck_inventory_cost_layers_quantities", "ck_inventory_cost_layers_status_matches_remaining"), lambda: insert_layer(conn, original_quantity=0, remaining_quantity=0, status="CLOSED"))
    _rejects(conn, "ck_inventory_cost_layers_quantities", lambda: insert_layer(conn, remaining_quantity=11))
    _rejects(conn, ("ck_inventory_cost_layers_quantities", "ck_inventory_cost_layers_status_matches_remaining"), lambda: insert_layer(conn, remaining_quantity=-1))
    _rejects(conn, "ck_inventory_cost_layers_status_matches_remaining", lambda: insert_layer(conn, status="CLOSED"))
    _rejects(conn, "ck_inventory_cost_layers_status_matches_remaining", lambda: insert_layer(conn, remaining_quantity=0))
    _rejects(conn, "ck_inventory_cost_layers_unit_cost", lambda: insert_layer(conn, unit_cost=-1))
    _rejects(conn, "ck_inventory_cost_layers_currency", lambda: insert_layer(conn, currency_code="co"))
    insert_layer(conn, company_product_id=uuid4(), currency_code=None)  # solo una apertura puede no tener moneda
    _rejects(
        conn,
        "ck_inventory_cost_layers_currency",
        lambda: insert_layer(conn, layer_kind="ADJUSTMENT", origin_movement_id=insert_movement(conn, op, line_index=2), currency_code=None),
    )


def test_only_openings_may_have_unknown_cost(conn) -> None:
    """Punto 1: ninguna capa nueva sin costo conocido, salvo la apertura (FR-063)."""
    op = insert_operation(conn)
    insert_layer(conn, cost_known=False, unit_cost=0)
    _rejects(conn, "ck_inventory_cost_layers_cost_known", lambda: insert_layer(conn, cost_known=False, unit_cost=5))
    _rejects(
        conn,
        "ck_inventory_cost_layers_cost_known",
        lambda: insert_layer(conn, layer_kind="ENTRY", origin_movement_id=insert_movement(conn, op), cost_known=False, unit_cost=0),
    )


def test_one_opening_layer_per_balance(conn) -> None:
    company, branch, product = uuid4(), uuid4(), uuid4()
    insert_layer(conn, company_id=company, branch_id=branch, company_product_id=product)
    _rejects(
        conn,
        "uq_inventory_cost_layers_opening",
        lambda: insert_layer(conn, company_id=company, branch_id=branch, company_product_id=product),
    )


# inventory_cost_consumptions ---------------------------------------------------


def test_consumption_rules(conn) -> None:
    op = insert_operation(conn)
    movement = insert_movement(conn, op)
    layer = insert_layer(conn)
    consumed = insert_consumption(conn, movement, layer)
    insert_consumption(conn, movement, layer, consumption_type="RESTORE", restores_consumption_id=consumed)
    _rejects(
        conn,
        "uq_inventory_cost_consumptions_restores",
        lambda: insert_consumption(conn, movement, layer, consumption_type="RESTORE", restores_consumption_id=consumed),
    )
    _rejects(conn, ("ck_inventory_cost_consumptions_type", "ck_inventory_cost_consumptions_restore_link"), lambda: insert_consumption(conn, movement, layer, consumption_type="OTRO"))
    _rejects(conn, "ck_inventory_cost_consumptions_quantity_positive", lambda: insert_consumption(conn, movement, layer, quantity=0))
    _rejects(conn, "ck_inventory_cost_consumptions_restore_link", lambda: insert_consumption(conn, movement, layer, consumption_type="RESTORE"))
    _rejects(conn, "ck_inventory_cost_consumptions_restore_link", lambda: insert_consumption(conn, movement, layer, restores_consumption_id=consumed))
