"""Imágenes por presentación global: restricción (spec 024, FR-024-46 fase 4).

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-23

Toda imagen exige presentación (`ck_product_assets_image_requires_presentation`). Desde aquí ninguna imagen
queda en `uq_product_assets_primary` (que solo cubre filas sin presentación): el principal por producto aplica
solo a los tipos que no son imagen, y el de las imágenes es por presentación.

Guarda: solo se aplica si **no** existe ninguna imagen sin presentación (verificación de la migración en cero
errores). Con alguna, aborta sin cambios e indica cuántas faltan. `downgrade` retira solo el CHECK.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "product_assets"
REQUIRES_PRESENTATION = "asset_type <> 'IMAGE' OR global_product_presentation_id IS NOT NULL"


def upgrade() -> None:
    """Exige presentación en toda imagen, solo si la migración dejó cero imágenes sin presentación."""
    pending = op.get_bind().execute(
        sa.text(f"SELECT count(*) FROM {TABLE} WHERE asset_type = 'IMAGE' AND global_product_presentation_id IS NULL")
    ).scalar_one()
    if pending:
        raise RuntimeError(
            f"Spec 024: {pending} imágenes sin presentación. Ejecute y verifique el relleno "
            "(product_catalog_service.tools.migrate_presentation_images) antes de aplicar la revisión 0006."
        )
    op.create_check_constraint(op.f("ck_product_assets_image_requires_presentation"), TABLE, REQUIRES_PRESENTATION)


def downgrade() -> None:
    """Retira la exigencia de presentación (vuelve a la etapa de transición)."""
    op.drop_constraint(op.f("ck_product_assets_image_requires_presentation"), TABLE, type_="check")
