"""Ventas sin impuesto adicional durante el MVP (spec 021, B-4 provisional; FR-021-30).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15

El precio de la lista de Commercial Relationship es el importe final que paga el cliente: `tax_amount` solo admite
`0` (`ck_sale_details_no_tax`). **No es una solución fiscal**: no separa el impuesto incluido en el precio ni factura
electrónicamente; una spec tributaria posterior lo sustituirá.

**Guarda** (DS-09): si alguna línea existente tiene impuesto, la migración se detiene **sin cambios** (hace falta
una decisión humana). No se modifica ninguna fila.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHECK = "ck_sale_details_no_tax"


def upgrade() -> None:
    with_tax = op.get_bind().execute(sa.text("SELECT count(*) FROM sale_details WHERE tax_amount <> 0")).scalar_one()
    if with_tax:
        raise RuntimeError(
            f"La migración 0003 de Sales se detuvo sin cambios: hay {with_tax} líneas de venta con impuesto. "
            "Hace falta una decisión humana antes de repetirla."
        )
    op.create_check_constraint(op.f(CHECK), "sale_details", "tax_amount = 0")


def downgrade() -> None:
    op.drop_constraint(op.f(CHECK), "sale_details", type_="check")
