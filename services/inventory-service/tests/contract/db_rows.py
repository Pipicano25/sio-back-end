"""Inserciones directas válidas para las pruebas de restricciones e inmutabilidad."""

from __future__ import annotations

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


def insert_movement(connection, operation_id: UUID, **overrides: Any) -> UUID:
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
        "unit_cost": None,
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
    values.update(overrides)
    connection.execute(
        text(
            "INSERT INTO inventory_movements (id, operation_id, company_id, branch_id, company_product_id, "
            "movement_type, quantity, previous_balance, new_balance, balance_sequence, unit_cost, origin_type, "
            "origin_id, origin_detail_id, line_index, application_user_id, correlation_id, reason, "
            "reversed_movement_id, created_by, updated_by) VALUES (:id, :operation_id, :company_id, :branch_id, "
            ":company_product_id, :movement_type, :quantity, :previous_balance, :new_balance, :balance_sequence, "
            ":unit_cost, :origin_type, :origin_id, :origin_detail_id, :line_index, :application_user_id, "
            ":correlation_id, :reason, :reversed_movement_id, :created_by, :updated_by)"
        ),
        values,
    )
    return values["id"]
