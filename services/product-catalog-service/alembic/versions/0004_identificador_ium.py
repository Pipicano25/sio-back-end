"""Tipo de identificador `IUM` (Identificador Único de Medicamento; spec 018).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-13

Amplía el CHECK de tipos con `IUM`, exige su formato y su presentación, y lo hace único en todo el catálogo
(incluidos inactivos). No transforma datos: ninguna fila existente es de tipo `IUM`.
`downgrade` restaura el CHECK anterior; si existen filas `IUM`, PostgreSQL rechaza la reversión y no se borra
ningún dato (deben retirarse antes, por decisión humana).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "global_product_identifiers"
TYPES_BEFORE = "identifier_type IN ('GTIN','EAN','UPC','BARCODE','OTHER')"
TYPES_AFTER = "identifier_type IN ('GTIN','EAN','UPC','BARCODE','OTHER','IUM')"
IUM_FORMAT = (
    "identifier_type <> 'IUM' OR (global_product_presentation_id IS NOT NULL"
    " AND value ~ '^[0-9][A-Z][0-9]{13}$' AND canonical_value = value)"
)


def upgrade() -> None:
    """Agrega el tipo IUM con formato, presentación obligatoria y unicidad global."""
    op.drop_constraint(op.f("ck_global_product_identifiers_type"), TABLE, type_="check")
    op.create_check_constraint(op.f("ck_global_product_identifiers_type"), TABLE, TYPES_AFTER)
    op.create_check_constraint(op.f("ck_global_product_identifiers_ium_format"), TABLE, IUM_FORMAT)
    op.create_index(
        "uq_global_product_identifiers_ium",
        TABLE,
        ["value"],
        unique=True,
        postgresql_where="identifier_type = 'IUM'",
    )


def downgrade() -> None:
    """Restaura los tipos anteriores (falla sin borrar datos si existen identificadores IUM)."""
    op.drop_index("uq_global_product_identifiers_ium", table_name=TABLE, postgresql_where="identifier_type = 'IUM'")
    op.drop_constraint(op.f("ck_global_product_identifiers_ium_format"), TABLE, type_="check")
    op.drop_constraint(op.f("ck_global_product_identifiers_type"), TABLE, type_="check")
    op.create_check_constraint(op.f("ck_global_product_identifiers_type"), TABLE, TYPES_BEFORE)
