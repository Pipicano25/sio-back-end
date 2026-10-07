"""Inserciones directas para probar restricciones y triggers sin pasar por la API."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Connection

ACTOR = "sub-prueba"


def insert_purchase(connection: Connection, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "company_id": uuid4(),
        "branch_id": uuid4(),
        "company_supplier_id": uuid4(),
        "payment_condition_code_snapshot": "CASH",
        "payment_terms_days_snapshot": 0,
        "due_date": "2026-10-06",
        "status": "DRAFT",
        "operation_date": "2026-10-06",
        "supplier_name_snapshot": "Proveedor ficticio",
        "supplier_identification_snapshot": "NIT 900",
        "currency_code": "COP",
        "subtotal": 0,
        "discount_total": 0,
        "tax_total": 0,
        "total": 0,
        "created_by_user_id": uuid4(),
        "created_by": ACTOR,
        "updated_by": ACTOR,
    }
    values.update(overrides)
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    connection.execute(text(f"INSERT INTO purchases ({columns}) VALUES ({placeholders})"), values)
    return values["id"]


def insert_detail(connection: Connection, purchase_id: UUID, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "purchase_id": purchase_id,
        "line_number": 1,
        "company_product_id": uuid4(),
        "product_code_snapshot": "001",
        "product_name_snapshot": "Producto",
        "base_quantity_factor_snapshot": 1,
        "unit_code_snapshot": "UND",
        "quantity": 1,
        "unit_cost": 10,
        "discount_amount": 0,
        "tax_amount": 0,
        "subtotal": 10,
        "total": 10,
        "created_by": ACTOR,
        "updated_by": ACTOR,
    }
    values.update(overrides)
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    connection.execute(text(f"INSERT INTO purchase_details ({columns}) VALUES ({placeholders})"), values)
    return values["id"]


def insert_sequence(connection: Connection, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "company_id": uuid4(),
        "branch_id": None,
        "document_kind": "PURCHASE",
        "series_code": "S1",
        "prefix": "CP",
        "separator": "-",
        "initial_number": 1,
        "number_length": 6,
        "reset_policy": "NEVER",
        "created_by": ACTOR,
        "updated_by": ACTOR,
    }
    values.update(overrides)
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    connection.execute(text(f"INSERT INTO purchase_sequences ({columns}) VALUES ({placeholders})"), values)
    return values["id"]


def insert_operation(connection: Connection, purchase_id: UUID, company_id: UUID, **overrides: Any) -> UUID:
    values: dict[str, Any] = {
        "id": uuid4(),
        "company_id": company_id,
        "purchase_id": purchase_id,
        "operation_type": "CONFIRM",
        "idempotency_key": f"k-{uuid4()}",
        "status": "PENDING",
        "correlation_id": uuid4(),
        "application_user_id": uuid4(),
        "started_at": "2026-10-06T00:00:00Z",
        "created_by": ACTOR,
        "updated_by": ACTOR,
    }
    values.update(overrides)
    if values["operation_type"] == "CANCEL":
        values.setdefault("reason", "Motivo de prueba")
    columns = ", ".join(values)
    placeholders = ", ".join(f":{name}" for name in values)
    connection.execute(text(f"INSERT INTO purchase_operations ({columns}) VALUES ({placeholders})"), values)
    return values["id"]


def confirmed_overrides(sequence_id: UUID) -> dict[str, Any]:
    return {
        "status": "CONFIRMED",
        "number": f"CP-{uuid4().hex[:6]}",
        "sequence_value": 1,
        "purchase_sequence_id": sequence_id,
        "inventory_operation_id": uuid4(),
    }
