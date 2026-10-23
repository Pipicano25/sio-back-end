"""Imágenes por presentación global: ampliación (spec 024, FR-024-46 fase 1).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-23

Agrega `product_assets.global_product_presentation_id` (opcional) con integridad compuesta (presentación,
producto) hacia `global_product_presentations`, igual que los identificadores (spec 018). Solo una imagen puede
tener presentación (`ck_product_assets_presentation_only_image`).

El principal único pasa a dos índices parciales que conviven durante la migración (research R1):

- `uq_product_assets_primary`: por producto y tipo, solo para filas **sin** presentación (los tipos que no son
  imagen y las imágenes aún sin migrar);
- `uq_product_assets_presentation_primary`: por presentación y tipo, para filas **con** presentación.

No transforma datos: el relleno lo hace `product_catalog_service.tools.migrate_presentation_images`.
`downgrade` restaura el índice anterior y retira la columna. Si el relleno dejó dos imágenes principales en un
mismo producto, PostgreSQL rechaza la reversión sin borrar datos: primero se revierte el relleno con su evidencia.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "product_assets"
COLUMN = "global_product_presentation_id"
PRIMARY_BEFORE = "is_primary AND status = 'ACTIVE'"
PRIMARY_PRODUCT = "is_primary AND status = 'ACTIVE' AND global_product_presentation_id IS NULL"
PRIMARY_PRESENTATION = "is_primary AND status = 'ACTIVE' AND global_product_presentation_id IS NOT NULL"
ONLY_IMAGE = "asset_type = 'IMAGE' OR global_product_presentation_id IS NULL"


def upgrade() -> None:
    """Agrega la presentación de la imagen y el principal por presentación."""
    op.add_column(TABLE, sa.Column(COLUMN, sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_product_assets_presentation_product",
        TABLE,
        "global_product_presentations",
        [COLUMN, "global_product_id"],
        ["id", "global_product_id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(op.f("ck_product_assets_presentation_only_image"), TABLE, ONLY_IMAGE)
    op.create_index("ix_product_assets_global_product_presentation_id", TABLE, [COLUMN])
    op.drop_index("uq_product_assets_primary", table_name=TABLE, postgresql_where=PRIMARY_BEFORE)
    op.create_index(
        "uq_product_assets_primary",
        TABLE,
        ["global_product_id", "asset_type"],
        unique=True,
        postgresql_where=PRIMARY_PRODUCT,
    )
    op.create_index(
        "uq_product_assets_presentation_primary",
        TABLE,
        [COLUMN, "asset_type"],
        unique=True,
        postgresql_where=PRIMARY_PRESENTATION,
    )


def downgrade() -> None:
    """Restaura el principal por producto y retira la presentación (falla sin borrar datos si hay conflicto)."""
    op.drop_index("uq_product_assets_presentation_primary", table_name=TABLE, postgresql_where=PRIMARY_PRESENTATION)
    op.drop_index("uq_product_assets_primary", table_name=TABLE, postgresql_where=PRIMARY_PRODUCT)
    op.create_index(
        "uq_product_assets_primary",
        TABLE,
        ["global_product_id", "asset_type"],
        unique=True,
        postgresql_where=PRIMARY_BEFORE,
    )
    op.drop_index("ix_product_assets_global_product_presentation_id", table_name=TABLE)
    op.drop_constraint(op.f("ck_product_assets_presentation_only_image"), TABLE, type_="check")
    op.drop_constraint("fk_product_assets_presentation_product", TABLE, type_="foreignkey")
    op.drop_column(TABLE, COLUMN)
