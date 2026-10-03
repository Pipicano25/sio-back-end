"""widen global business sector name (Fase B, CIIU Rev. 5 A.C.)

Los títulos oficiales de la CIIU Rev. 5 A.C. del DANE llegan a 222 caracteres
(división 15); `name` pasa de 180 a 255 para no recortarlos (FR-056; sesión
2026-10-02 de la spec). La reversión solo es posible si ningún nombre supera
180 caracteres.

Revision ID: 0018_widen_sector_name
Revises: 0017_create_legal_reps
Create Date: 2026-10-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0018_widen_sector_name"
down_revision: Union[str, Sequence[str], None] = "0017_create_legal_reps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE = "global_business_sectors"


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        TABLE,
        "name",
        existing_type=sa.String(length=180),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    too_long = op.get_bind().execute(
        sa.text(f"SELECT count(*) FROM {TABLE} WHERE char_length(name) > 180")
    ).scalar_one()

    if too_long:
        raise RuntimeError(
            f"No se puede revertir 0018: {too_long} sectores tienen un nombre de más de "
            "180 caracteres (títulos oficiales de la CIIU Rev. 5 A.C.)."
        )

    op.alter_column(
        TABLE,
        "name",
        existing_type=sa.String(length=255),
        type_=sa.String(length=180),
        existing_nullable=False,
    )
