"""Vistas de contrato v1 de Product Catalog (constitución 3.0.0, D27; spec 025, T038).

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-16

Crea el esquema ``contract`` y tres vistas de solo lectura para los consumidores (contracts/contract-views.md):

- ``v1_products``: ``id``, ``status``, ``base_unit_id`` (reemplaza ``GET /products/{id}``).
- ``v1_presentations``: ``id``, ``global_product_id``, ``code``, ``name``, ``status``, ``base_quantity``
  (reemplaza ``GET /presentations/{id}`` y ``presentations/batch-lookup``). Sin columnas de imagen.
- ``v1_units_of_measure``: ``id``, ``code``, ``name``, ``status``, ``measurement_type``, ``allows_decimals``
  (reemplaza ``GET /units-of-measure/{id}`` y ``units-of-measure/batch-lookup``).

Las vistas de resumen (``v1_product_summary*``) llegan en otra migración. Los cambios compatibles se hacen con
``CREATE OR REPLACE VIEW`` agregando columnas al final; un cambio incompatible crea ``v2_``. Los roles de lectura no
se crean aquí (infrastructure/scripts/contract-readers, con ``contract/grants.yaml``).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VIEWS = ("v1_products", "v1_presentations", "v1_units_of_measure")

PRODUCTS = """
CREATE OR REPLACE VIEW contract.v1_products AS
SELECT p.id, p.status, p.base_unit_id
  FROM public.global_products p
"""

PRESENTATIONS = """
CREATE OR REPLACE VIEW contract.v1_presentations AS
SELECT pp.id, pp.global_product_id, pp.code, pp.name, pp.status, pp.base_quantity
  FROM public.global_product_presentations pp
"""

UNITS_OF_MEASURE = """
CREATE OR REPLACE VIEW contract.v1_units_of_measure AS
SELECT u.id, u.code, u.name, u.status, u.measurement_type, u.allows_decimals
  FROM public.global_units_of_measure u
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    for statement in (PRODUCTS, PRESENTATIONS, UNITS_OF_MEASURE):
        op.execute(statement)
    for view in VIEWS:
        op.execute(f"COMMENT ON VIEW contract.{view} IS 'Vista de contrato de product-catalog (D27, spec 025).'")


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
