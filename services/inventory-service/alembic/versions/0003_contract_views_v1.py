"""Vistas de contrato v1 de Inventory (constitución 3.0.0, D27; spec 025, T041).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-16

Crea el esquema ``contract`` y tres vistas de solo lectura (contracts/contract-views.md):

- ``v1_balances``: una fila por saldo registrado (``inventory_balances``). Reemplaza ``balances/lookup``. Un
  producto sin saldo **no tiene fila**: el API lo devuelve con ``quantity = 0`` y ``balance_sequence = 0`` y el
  consumidor hace lo mismo. ``balance_sequence`` es ``inventory_balances.version``, como en el API.
- ``v1_operations_by_key``: una fila por operación (todas están confirmadas: la tabla es de solo inserción y la
  operación se escribe en la misma transacción que sus movimientos). Reemplaza la cabecera de
  ``GET /companies/{c}/inventory-operations/by-key/{key}``. ``reversed_by_operation_id`` es el id de la operación
  que la revierte (el mismo campo del API) y ``status`` se deriva de él: ``REVERSED`` si existe, ``APPLIED`` si no.
  El API no expone ``status``; la columna existe porque la exige el contrato.
- ``v1_operation_movements``: los movimientos de cada operación, que el API anida en ``movements``. Se lee con
  ``ORDER BY line_index`` (único por operación), el mismo orden en que el API los lista. Sales solo los usa en
  operaciones ``OUTPUT`` (``origin_detail_id``, ``unit_cost``, ``movement_value``, ``cost_known``).

Decisión: dos vistas en vez de una fila por movimiento con la cabecera repetida, para que una operación sea
exactamente una fila (la existencia de la clave se comprueba sin depender de que tenga movimientos) y para que la
cabecera no cambie si en el futuro se agregan columnas de movimiento.

Los cambios compatibles se hacen con ``CREATE OR REPLACE VIEW`` agregando columnas al final; un cambio
incompatible crea ``v2_``. Los roles de lectura no se crean aquí (infrastructure/scripts/contract-readers).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEWS = ("v1_balances", "v1_operations_by_key", "v1_operation_movements")

BALANCES = """
CREATE OR REPLACE VIEW contract.v1_balances AS
SELECT b.company_id,
       b.branch_id,
       b.company_product_id,
       b.quantity,
       b.version AS balance_sequence
  FROM public.inventory_balances b
"""

OPERATIONS_BY_KEY = """
CREATE OR REPLACE VIEW contract.v1_operations_by_key AS
SELECT o.company_id,
       o.operation_key,
       o.id AS operation_id,
       o.operation_type,
       (CASE WHEN r.id IS NULL THEN 'APPLIED' ELSE 'REVERSED' END)::varchar(20) AS status,
       o.branch_id,
       o.reverses_operation_id,
       r.id AS reversed_by_operation_id,
       o.created_at
  FROM public.inventory_operations o
  LEFT JOIN public.inventory_operations r ON r.reverses_operation_id = o.id
"""

OPERATION_MOVEMENTS = """
CREATE OR REPLACE VIEW contract.v1_operation_movements AS
SELECT m.operation_id,
       m.company_id,
       m.line_index,
       m.id AS movement_id,
       m.origin_detail_id,
       m.company_product_id,
       m.movement_type,
       m.quantity,
       m.unit_cost,
       m.movement_value,
       m.cost_known,
       m.reversed_movement_id
  FROM public.inventory_movements m
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    for statement in (BALANCES, OPERATIONS_BY_KEY, OPERATION_MOVEMENTS):
        op.execute(statement)
    for view in VIEWS:
        op.execute(f"COMMENT ON VIEW contract.{view} IS 'Vista de contrato de inventory (D27, spec 025).'")


def downgrade() -> None:
    for view in reversed(VIEWS):
        op.execute(f"DROP VIEW IF EXISTS contract.{view}")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'contract'
            ) THEN
                DROP SCHEMA IF EXISTS contract;
            END IF;
        END $$
        """
    )
