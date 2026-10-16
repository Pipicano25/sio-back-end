"""Hechos de costo para precios automáticos e impuesto por tasa (spec 021).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-15

- **Impuesto por tasa** (FR-021-09..12): `purchase_details.tax_percentage` (0 a 100, 4 decimales) y
  `tax_percentage_source` (`PRODUCT_DEFAULT` / `LINE_OVERRIDE`), ambos NULL en las compras anteriores. Las líneas ya
  quedan congeladas fuera de `DRAFT` por `tr_purchase_details_draft_only` (0001); no hace falta otro trigger.
- **Sin presentaciones repetidas** (FR-021-13): `uq_purchase_details_purchase_presentation`.
- **Serie de costos por presentación** (FR-021-14, R-03): `purchase_presentation_cost_series` (infraestructura, D23):
  última secuencia y hechos de la última recepción de cada presentación en la empresa. La secuencia solo avanza de
  uno en uno.
- **Outbox de solicitudes de precio** (FR-021-15, FR-021-16, EXC-001): `purchase_price_update_outbox` (D26). El
  contenido es inmutable; solo cambian los datos de entrega.

**Guarda** (DS-09): si ya hay compras con la misma presentación en dos líneas, la migración se detiene **sin
cambios**: hace falta una decisión humana. Ninguna fila existente se modifica. `downgrade` se detiene sin cambios si
ya existen datos de la spec 021.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0003'
down_revision: Union[str, Sequence[str], None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SERIES = "purchase_presentation_cost_series"
OUTBOX = "purchase_price_update_outbox"

GUARDS = (
    (
        "SELECT count(*) FROM (SELECT purchase_id, company_product_presentation_id FROM purchase_details "
        "GROUP BY purchase_id, company_product_presentation_id HAVING count(*) > 1) AS repeated",
        "compras con la misma presentación en más de una línea",
    ),
)

DOWNGRADE_GUARDS = (
    (f"SELECT count(*) FROM {OUTBOX}", "solicitudes de actualización de precio"),
    (f"SELECT count(*) FROM {SERIES}", "series de costos por presentación"),
    ("SELECT count(*) FROM purchase_details WHERE tax_percentage IS NOT NULL", "líneas con tasa de impuesto"),
)

SERIES_ADVANCE = """
CREATE FUNCTION purchase_cost_series_advance() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF (NEW.company_id, NEW.company_product_presentation_id) IS DISTINCT FROM
       (OLD.company_id, OLD.company_product_presentation_id) OR NEW.last_sequence <> OLD.last_sequence + 1 THEN
        RAISE EXCEPTION 'La serie de costos de la presentación % solo avanza de uno en uno.',
            OLD.company_product_presentation_id USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

OUTBOX_DELIVERY_ONLY = """
CREATE FUNCTION purchase_price_update_outbox_delivery_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'DELIVERED' THEN
        RAISE EXCEPTION 'La solicitud de precio % ya fue entregada y no cambia.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF (NEW.id, NEW.company_id, NEW.company_product_presentation_id, NEW.sequence, NEW.purchase_id,
        NEW.purchase_detail_id, NEW.payload, NEW.created_at, NEW.created_by)
       IS DISTINCT FROM
       (OLD.id, OLD.company_id, OLD.company_product_presentation_id, OLD.sequence, OLD.purchase_id,
        OLD.purchase_detail_id, OLD.payload, OLD.created_at, OLD.created_by) THEN
        RAISE EXCEPTION 'El contenido de la solicitud de precio % es inmutable.', OLD.id
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$;
"""

TRIGGERS = (
    f"CREATE TRIGGER tr_{SERIES}_advance BEFORE UPDATE ON {SERIES} "
    "FOR EACH ROW EXECUTE FUNCTION purchase_cost_series_advance()",
    f"CREATE TRIGGER tr_{SERIES}_no_delete BEFORE DELETE ON {SERIES} "
    "FOR EACH ROW EXECUTE FUNCTION purchase_reject_change()",
    f"CREATE TRIGGER tr_{OUTBOX}_delivery_only BEFORE UPDATE ON {OUTBOX} "
    "FOR EACH ROW EXECUTE FUNCTION purchase_price_update_outbox_delivery_only()",
    f"CREATE TRIGGER tr_{OUTBOX}_no_delete BEFORE DELETE ON {OUTBOX} "
    "FOR EACH ROW EXECUTE FUNCTION purchase_reject_change()",
)


def _stop_if_any(guards, step: str) -> None:
    connection = op.get_bind()
    for query, description in guards:
        count = connection.execute(sa.text(query)).scalar_one()
        if count:
            raise RuntimeError(
                f"La migración 0003 de Purchase ({step}) se detuvo sin cambios: hay {count} {description}. "
                "Hace falta una decisión humana antes de repetirla."
            )


def upgrade() -> None:
    _stop_if_any(GUARDS, "upgrade")
    op.add_column("purchase_details", sa.Column("tax_percentage", sa.Numeric(7, 4), nullable=True))
    op.add_column("purchase_details", sa.Column("tax_percentage_source", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        op.f("ck_purchase_details_tax_percentage"),
        "purchase_details",
        "tax_percentage IS NULL OR (tax_percentage >= 0 AND tax_percentage <= 100)",
    )
    op.create_check_constraint(
        op.f("ck_purchase_details_tax_percentage_source"),
        "purchase_details",
        "(tax_percentage IS NULL AND tax_percentage_source IS NULL) OR (tax_percentage IS NOT NULL "
        "AND tax_percentage_source IN ('PRODUCT_DEFAULT', 'LINE_OVERRIDE'))",
    )
    op.create_unique_constraint(
        "uq_purchase_details_purchase_presentation",
        "purchase_details",
        ["purchase_id", "company_product_presentation_id"],
    )

    op.create_table(
        SERIES,
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("company_product_presentation_id", sa.UUID(), nullable=False),
        sa.Column("last_sequence", sa.Integer(), nullable=False),
        sa.Column("last_purchase_detail_id", sa.UUID(), nullable=False),
        sa.Column("last_line_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("last_quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["last_purchase_detail_id"], ["purchase_details.id"], name=op.f(f"fk_{SERIES}_last_purchase_detail_id_purchase_details")
        ),
        sa.PrimaryKeyConstraint("company_id", "company_product_presentation_id", name=op.f(f"pk_{SERIES}")),
        sa.CheckConstraint("last_sequence > 0", name=op.f(f"ck_{SERIES}_last_sequence")),
        sa.CheckConstraint("last_quantity > 0", name=op.f(f"ck_{SERIES}_last_quantity")),
    )

    op.create_table(
        OUTBOX,
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("company_product_presentation_id", sa.UUID(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("purchase_id", sa.UUID(), nullable=False),
        sa.Column("purchase_detail_id", sa.UUID(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=12), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_error_code", sa.String(length=60), nullable=True),
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["purchase_id"], ["purchases.id"], name=op.f(f"fk_{OUTBOX}_purchase_id_purchases")),
        sa.ForeignKeyConstraint(
            ["purchase_detail_id"], ["purchase_details.id"], name=op.f(f"fk_{OUTBOX}_purchase_detail_id_purchase_details")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{OUTBOX}")),
        sa.UniqueConstraint("purchase_detail_id", name=op.f(f"uq_{OUTBOX}_purchase_detail_id")),
        sa.UniqueConstraint(
            "company_id", "company_product_presentation_id", "sequence", name="uq_purchase_price_update_outbox_sequence"
        ),
        sa.CheckConstraint("sequence > 0", name=op.f(f"ck_{OUTBOX}_sequence")),
        sa.CheckConstraint("status IN ('PENDING', 'DELIVERED')", name=op.f(f"ck_{OUTBOX}_status")),
        sa.CheckConstraint("attempts >= 0", name=op.f(f"ck_{OUTBOX}_attempts")),
        sa.CheckConstraint("(status = 'DELIVERED') = (delivered_at IS NOT NULL)", name=op.f(f"ck_{OUTBOX}_delivery")),
    )
    op.create_index(
        "ix_purchase_price_update_outbox_pending",
        OUTBOX,
        ["company_id", "company_product_presentation_id", "sequence"],
        postgresql_where=sa.text("status = 'PENDING'"),
    )

    op.execute(SERIES_ADVANCE)
    op.execute(OUTBOX_DELIVERY_ONLY)
    for statement in TRIGGERS:
        op.execute(statement)


def downgrade() -> None:
    _stop_if_any(DOWNGRADE_GUARDS, "downgrade")
    op.drop_table(OUTBOX)
    op.drop_table(SERIES)
    op.execute("DROP FUNCTION purchase_price_update_outbox_delivery_only()")
    op.execute("DROP FUNCTION purchase_cost_series_advance()")
    op.drop_constraint("uq_purchase_details_purchase_presentation", "purchase_details", type_="unique")
    op.drop_constraint(op.f("ck_purchase_details_tax_percentage_source"), "purchase_details", type_="check")
    op.drop_constraint(op.f("ck_purchase_details_tax_percentage"), "purchase_details", type_="check")
    op.drop_column("purchase_details", "tax_percentage_source")
    op.drop_column("purchase_details", "tax_percentage")
