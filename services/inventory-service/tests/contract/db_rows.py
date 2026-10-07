"""Inserciones directas válidas para las pruebas de restricciones e inmutabilidad."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

HASH = "a" * 64


def insert_operation(connection, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "operation_key": uuid4(),
        "requested_by_client": "inventory-test-operator",
        "operation_type": "ENTRY",
        "company_id": uuid4(),
        "branch_id": uuid4(),
        "origin_type": "PURCHASE",
        "origin_id": uuid4(),
        "application_user_id": uuid4(),
        "correlation_id": uuid4(),
        "reason": None,
        "reverses_operation_id": None,
        "line_count": 1,
        "request_hash": HASH,
        "created_by": "sub-sa-inventory-test-operator",
    }
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO inventory_operations (id, operation_key, requested_by_client, operation_type, "
            "company_id, branch_id, origin_type, origin_id, application_user_id, correlation_id, reason, "
            "reverses_operation_id, line_count, request_hash, created_by) VALUES (:id, :operation_key, "
            ":requested_by_client, :operation_type, :company_id, :branch_id, :origin_type, :origin_id, "
            ":application_user_id, :correlation_id, :reason, :reverses_operation_id, :line_count, "
            ":request_hash, :created_by)"
        ),
        values,
    )
    return values["id"]


def insert_balance(connection, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "company_id": uuid4(),
        "branch_id": uuid4(),
        "company_product_id": uuid4(),
        "quantity": 0,
        "version": 0,
        "created_by": "sub",
        "updated_by": "sub",
    }
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO inventory_balances (id, company_id, branch_id, company_product_id, quantity, version, "
            "created_by, updated_by) VALUES (:id, :company_id, :branch_id, :company_product_id, :quantity, "
            ":version, :created_by, :updated_by)"
        ),
        values,
    )
    return values["id"]


def insert_movement(connection, operation_id: UUID, *, valued: bool = True, **overrides: Any) -> UUID:
    """Movimiento directo. `valued=False` usa solo las columnas de la `0001` (siembra de la Fase A)."""
    values: dict[str, Any] = {
        "id": uuid4(),
        "operation_id": operation_id,
        "company_id": uuid4(),
        "branch_id": uuid4(),
        "company_product_id": uuid4(),
        "movement_type": "PURCHASE_ENTRY",
        "quantity": 10,
        "previous_balance": 0,
        "new_balance": 10,
        "balance_sequence": 1,
        "unit_cost": 1000 if valued else None,
        "origin_type": "PURCHASE",
        "origin_id": uuid4(),
        "origin_detail_id": uuid4(),
        "line_index": 0,
        "application_user_id": uuid4(),
        "correlation_id": uuid4(),
        "reason": None,
        "reversed_movement_id": None,
        "created_by": "sub",
        "updated_by": "sub",
    }
    if valued:
        values["movement_value"] = 10000
        values["cost_known"] = True
    values.update(overrides)
    columns = list(values)
    connection.execute(
        text(
            f"INSERT INTO inventory_movements ({', '.join(columns)}) "
            f"VALUES ({', '.join(':' + name for name in columns)})"
        ),
        values,
    )
    return values["id"]


def _insert(connection, table: str, values: dict[str, Any]) -> UUID:
    columns = list(values)
    connection.execute(
        text(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(':' + name for name in columns)})"),
        values,
    )
    return values["id"]


def insert_layer(connection, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "company_id": uuid4(),
        "branch_id": uuid4(),
        "company_product_id": uuid4(),
        "layer_kind": "OPENING",
        "origin_movement_id": None,
        "original_quantity": 10,
        "remaining_quantity": 10,
        "unit_cost": 1000,
        "cost_known": True,
        "currency_code": "COP",
        "received_at": datetime(2026, 10, 6, tzinfo=UTC),
        "status": "OPEN",
        "created_by": "sub",
        "updated_by": "sub",
    }
    values.update(overrides)
    return _insert(connection, "inventory_cost_layers", values)


def insert_consumption(connection, movement_id: UUID, layer_id: UUID, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "movement_id": movement_id,
        "cost_layer_id": layer_id,
        "consumption_type": "CONSUME",
        "restores_consumption_id": None,
        "quantity": 2,
        "unit_cost": 1000,
        "cost_known": True,
        "cost_amount": 2000,
        "created_by": "sub",
    }
    values.update(overrides)
    return _insert(connection, "inventory_cost_consumptions", values)


def insert_count(connection, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "company_id": uuid4(),
        "branch_id": uuid4(),
        "status": "DRAFT",
        "started_by_user_id": uuid4(),
        "started_at": None,
        "completed_by_user_id": None,
        "completed_at": None,
        "cancelled_by_user_id": None,
        "cancelled_at": None,
        "cancel_reason": None,
        "operation_id": None,
        "observations": None,
        "created_by": "sub",
        "updated_by": "sub",
    }
    values.update(overrides)
    return _insert(connection, "inventory_counts", values)


def insert_count_detail(connection, count_id: UUID, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "inventory_count_id": count_id,
        "company_product_id": uuid4(),
        "system_quantity_snapshot": 10,
        "counted_quantity": 8,
        "difference_quantity": -2,
        "unit_cost": None,
        "inventory_adjustment_id": None,
        "counted_by_user_id": uuid4(),
        "counted_at": datetime(2026, 10, 6, tzinfo=UTC),
        "created_by": "sub",
        "updated_by": "sub",
    }
    values.update(overrides)
    return _insert(connection, "inventory_count_details", values)


def insert_adjustment(connection, operation_id: UUID, movement_id: UUID, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "operation_id": operation_id,
        "movement_id": movement_id,
        "company_id": uuid4(),
        "branch_id": uuid4(),
        "company_product_id": uuid4(),
        "adjustment_type": "NEGATIVE",
        "quantity": 3,
        "reason": "Producto dañado",
        "previous_balance": 10,
        "new_balance": 7,
        "unit_cost": 1000,
        "adjustment_value": 3000,
        "inventory_count_id": None,
        "application_user_id": uuid4(),
        "created_by": "sub",
        "updated_by": "sub",
    }
    values.update(overrides)
    return _insert(connection, "inventory_adjustments", values)


def insert_company_policy(connection, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "company_id": uuid4(),
        "inventory_system": "PERPETUAL",
        "valuation_method": "FIFO",
        "replenishment_strategy": "STANDARD",
        "created_by": "sub",
        "updated_by": "sub",
    }
    values.update(overrides)
    return _insert(connection, "company_inventory_policies", values)


def insert_policy(connection, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "company_id": uuid4(),
        "branch_id": uuid4(),
        "company_product_id": uuid4(),
        "minimum_stock": 5,
        "target_stock": 10,
        "service_level": "0.95",
        "safety_stock_method": "BASIC",
        "calculation_window_days": 90,
        "replenishment_mode": "MANUAL",
        "created_by": "sub",
        "updated_by": "sub",
    }
    values.update(overrides)
    return _insert(connection, "inventory_policies", values)
