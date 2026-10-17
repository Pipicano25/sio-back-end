"""Ayudas de las pruebas de la spec 022 (INV-1, INV-2, INV-3): saldos y políticas sembrados en la base de pruebas.

Se insertan filas directamente, solo en la base de pruebas, para fijar estados exactos (saldo positivo, saldo
registrado en cero, sin registro, políticas activas e inactivas) sin depender de entradas y salidas.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.engine import Engine

ACTOR = "fixture-spec022"


def insert_balance(
    engine: Engine,
    company: UUID,
    branch: UUID,
    product: UUID,
    quantity: str | Decimal,
    *,
    inventory_value: str | Decimal = "0",
    average_unit_cost: str | Decimal | None = None,
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO inventory_balances (company_id, branch_id, company_product_id, quantity, version, "
                "average_unit_cost, inventory_value, has_unknown_cost, created_by, updated_by) "
                "VALUES (:company, :branch, :product, :quantity, 1, :avg, :value, false, :actor, :actor)"
            ),
            {
                "company": company,
                "branch": branch,
                "product": product,
                "quantity": Decimal(str(quantity)),
                "avg": None if average_unit_cost is None else Decimal(str(average_unit_cost)),
                "value": Decimal(str(inventory_value)),
                "actor": ACTOR,
            },
        )


def insert_policy(
    engine: Engine,
    company: UUID,
    branch: UUID,
    product: UUID,
    minimum: str | Decimal,
    *,
    active: bool = True,
) -> UUID:
    policy_id = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO inventory_policies (id, company_id, branch_id, company_product_id, minimum_stock, "
                "safety_stock_method, calculation_window_days, replenishment_mode, auto_purchase_enabled, is_active, "
                "version, created_by, updated_by) VALUES (:id, :company, :branch, :product, :minimum, 'BASIC', 90, "
                "'MANUAL', false, :active, 1, :actor, :actor)"
            ),
            {
                "id": policy_id,
                "company": company,
                "branch": branch,
                "product": product,
                "minimum": Decimal(str(minimum)),
                "active": active,
                "actor": ACTOR,
            },
        )
    return policy_id
