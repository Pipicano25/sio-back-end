"""Vista de contrato v1 de las políticas de inventario (constitución 3.0.0, D27; spec 025, T073).

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-17

Agrega al esquema ``contract`` la vista ``v1_inventory_policies`` (contracts/contract-views.md), que reemplaza
``POST /companies/{c}/branches/{b}/inventory-policies/lookup`` (INV-1) para PIQ:

- columnas ``company_id``, ``branch_id``, ``company_product_id``, ``minimum_stock``;
- una fila por política **activa** (``inventory_policies.is_active``), la misma que devuelve INV-1
  (``InventoryReadRepository.active_policies``). A lo sumo hay una por empresa, sucursal y producto
  (``uq_inventory_policies_active``). Un producto sin política activa no tiene fila: INV-1 responde ``policy: null``.

Los cambios compatibles se hacen con ``CREATE OR REPLACE VIEW`` agregando columnas al final; un cambio incompatible
crea ``v2_``. Los roles de lectura no se crean aquí (infrastructure/scripts/contract-readers).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

POLICIES = """
CREATE OR REPLACE VIEW contract.v1_inventory_policies AS
SELECT p.company_id,
       p.branch_id,
       p.company_product_id,
       p.minimum_stock
  FROM public.inventory_policies p
 WHERE p.is_active
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS contract")
    op.execute(POLICIES)
    op.execute("COMMENT ON VIEW contract.v1_inventory_policies IS 'Vista de contrato de inventory (D27, spec 025).'")


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS contract.v1_inventory_policies")
