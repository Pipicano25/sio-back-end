"""Elimina `sale_price` y `reference_cost` de `company_products` (spec 019: precios solo por presentación).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-13

`CompanyProduct` representa solo la asociación del producto global con la empresa: los precios de venta viven en
`price_list_items` (por presentación) y los costos en las compras y la valoración de Inventory.

Guarda (RC-PRC-5, FR-019-09): si algún producto tiene `sale_price` o `reference_cost` distinto de `0`, la migración
se detiene **sin cambios**, porque eliminaría valores comerciales; hace falta una decisión humana. Los `0` son los
valores por defecto del contrato anterior y no representan información.

`downgrade` vuelve a crear las columnas `NOT NULL DEFAULT 0` con sus `CHECK` (no hay valores que restaurar).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "company_products"


def upgrade() -> None:
    with_values = op.get_bind().execute(
        sa.text(f"SELECT count(*) FROM {TABLE} WHERE sale_price <> 0 OR reference_cost <> 0")
    ).scalar_one()
    if with_values:
        raise RuntimeError(
            f"La migración 0004 eliminaría precios o costos de {with_values} productos empresariales "
            "(sale_price o reference_cost distinto de 0). No se cambió nada: decida cómo conservarlos "
            "(por ejemplo, como precios por presentación en una lista) y repita la migración."
        )
    op.drop_constraint(op.f("ck_company_products_sale_price_non_negative"), TABLE, type_="check")
    op.drop_constraint(op.f("ck_company_products_reference_cost_non_negative"), TABLE, type_="check")
    op.drop_column(TABLE, "sale_price")
    op.drop_column(TABLE, "reference_cost")


def downgrade() -> None:
    op.add_column(TABLE, sa.Column("sale_price", sa.Numeric(18, 2), nullable=False, server_default="0"))
    op.add_column(TABLE, sa.Column("reference_cost", sa.Numeric(18, 4), nullable=False, server_default="0"))
    op.create_check_constraint(op.f("ck_company_products_sale_price_non_negative"), TABLE, "sale_price >= 0")
    op.create_check_constraint(op.f("ck_company_products_reference_cost_non_negative"), TABLE, "reference_cost >= 0")
