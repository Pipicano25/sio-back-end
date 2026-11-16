"""Vistas de contrato v1 de Payment Reference (constitución 3.0.0, D27; spec 025, T041).

Revision ID: 0005
Revises: 7c1d9e20a020
Create Date: 2026-11-16

Crea el esquema ``contract`` y dos vistas de solo lectura (contracts/contract-views.md):

- ``v1_payment_methods`` (``id``, ``code``, ``name``, ``status``): reemplaza ``GET /global-payment-methods/{id}``.
- ``v1_payment_condition_types`` (``id``, ``code``, ``status``): reemplaza
  ``GET /global-payment-condition-types/{id}``.

Las vistas incluyen filas activas e inactivas, como el GET por id; el consumidor decide qué hacer con ``status``.
Los cambios compatibles se hacen con ``CREATE OR REPLACE VIEW`` agregando columnas al final; un cambio
incompatible crea ``v2_``. Los roles de lectura no se crean aquí (infrastructure/scripts/contract-readers).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "7c1d9e20a020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEWS = ("v1_payment_methods", "v1_payment_condition_types")

PAYMENT_METHODS = """
CREATE OR REPLACE VIEW contract.v1_payment_methods AS
SELECT m.id, m.code, m.name, m.status
  FROM public.global_payment_methods m
"""

PAYMENT_CONDITION_TYPES = """
CREATE OR REPLACE VIEW contract.v1_payment_condition_types AS
SELECT t.id, t.code, t.status
  FROM public.global_payment_condition_types t
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    for statement in (PAYMENT_METHODS, PAYMENT_CONDITION_TYPES):
        op.execute(statement)
    for view in VIEWS:
        op.execute(f"COMMENT ON VIEW contract.{view} IS 'Vista de contrato de payment-reference (D27, spec 025).'")


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
