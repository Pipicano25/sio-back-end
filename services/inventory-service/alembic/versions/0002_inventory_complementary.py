"""Ajustes, conteos, políticas y valoración FIFO de inventario (013).

Cambios a la Fase A (`specs/013-inventory-complementary/data-model.md`):

- `inventory_operations`: tipo `ADJUSTMENT` con origen `ADJUSTMENT` o `COUNT`;
  hasta 1 000 líneas solo con origen `COUNT`.
- `inventory_movements`: tipos `POSITIVE_ADJUSTMENT` / `NEGATIVE_ADJUSTMENT`; `unit_cost`
  en todo movimiento valorizado; `movement_value` y `cost_known`.
  `ck_inventory_movements_valued` se crea **`NOT VALID`**: exige costo, valor y
  `cost_known` en toda fila nueva sin revalidar el historial inmutable de la Fase A.
- `inventory_balances`: `average_unit_cost`, `inventory_value`, `has_unknown_cost`.

Tablas nuevas: políticas de empresa y de producto, ajustes, conteos y sus detalles,
capas de costo y consumos, con sus triggers de inmutabilidad (R-12).

Capa de apertura (R-05, FR-057): cada saldo con cantidad recibe **una** capa
`OPENING` por su cantidad exacta, con el costo de su `PURCHASE_ENTRY` no revertida
de mayor `balance_sequence` que tenga costo, o `0` con `cost_known = false`
("sin costo"). `currency_code` queda nulo: la migración no consulta Operational
Context (decisión del 2026-10-06). El índice único parcial
`uq_inventory_cost_layers_opening` y `ON CONFLICT DO NOTHING` impiden duplicados;
al final, si alguna suma de capas abiertas no coincide con su saldo, la migración
falla y se revierte entera (la base queda en `0001`).

`downgrade` revierte la estructura; las capas de apertura se pierden con su tabla.
Solo es posible mientras no existan movimientos de la Fase B (ajustes o salidas
valorizadas), que las restricciones de la `0001` no admiten.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

QUANTITY = sa.Numeric(18, 4)
MONEY = sa.Numeric(18, 2)
MIGRATION_ACTOR = "sio-migration-0002"


class OpeningLayersMismatch(RuntimeError):
    """Tras crear las aperturas, la suma de capas abiertas no coincide con algún saldo."""


def _uuid(name: str, *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def _id() -> sa.Column:
    return sa.Column(
        "id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")
    )


def _timestamp(name: str, *, nullable: bool = False) -> sa.Column:
    if nullable:
        return sa.Column(name, sa.DateTime(timezone=True), nullable=True)
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


def _audit() -> list[sa.Column]:
    return [
        _timestamp("created_at"),
        sa.Column("created_by", sa.String(255), nullable=False),
        _timestamp("updated_at"),
        sa.Column("updated_by", sa.String(255), nullable=False),
    ]


def _replace_check(table: str, name: str, condition: str) -> None:
    op.drop_constraint(op.f(name), table, type_="check")
    op.create_check_constraint(op.f(name), table, condition)


# ----------------------------------------------------------------------------------
# Capa de apertura (R-05)
# ----------------------------------------------------------------------------------

OPENING_INSERT = f"""
INSERT INTO inventory_cost_layers (
    company_id, branch_id, company_product_id, layer_kind, origin_movement_id,
    original_quantity, remaining_quantity, unit_cost, cost_known, currency_code,
    received_at, status, created_at, created_by, updated_at, updated_by
)
SELECT b.company_id, b.branch_id, b.company_product_id, 'OPENING', NULL,
       b.quantity, b.quantity, COALESCE(c.unit_cost, 0), c.unit_cost IS NOT NULL, NULL,
       now(), 'OPEN', now(), '{MIGRATION_ACTOR}', now(), '{MIGRATION_ACTOR}'
FROM inventory_balances b
LEFT JOIN LATERAL (
    SELECT m.unit_cost
    FROM inventory_movements m
    WHERE m.company_id = b.company_id
      AND m.branch_id = b.branch_id
      AND m.company_product_id = b.company_product_id
      AND m.movement_type = 'PURCHASE_ENTRY'
      AND m.unit_cost IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM inventory_movements r WHERE r.reversed_movement_id = m.id)
    ORDER BY m.balance_sequence DESC
    LIMIT 1
) c ON true
WHERE b.quantity > 0
ON CONFLICT (company_id, branch_id, company_product_id) WHERE layer_kind = 'OPENING' DO NOTHING
"""

BALANCE_VALUATION_UPDATE = """
UPDATE inventory_balances b
SET inventory_value = v.value,
    average_unit_cost = CASE WHEN b.quantity > 0 THEN round(v.value / b.quantity, 4) END,
    has_unknown_cost = v.unknown
FROM (
    SELECT company_id, branch_id, company_product_id,
           sum(round(remaining_quantity * unit_cost, 2)) AS value,
           bool_or(NOT cost_known) AS unknown
    FROM inventory_cost_layers
    WHERE status = 'OPEN'
    GROUP BY company_id, branch_id, company_product_id
) v
WHERE b.company_id = v.company_id AND b.branch_id = v.branch_id AND b.company_product_id = v.company_product_id
"""

MISMATCH_QUERY = """
SELECT count(*)
FROM inventory_balances b
FULL JOIN (
    SELECT company_id, branch_id, company_product_id,
           sum(remaining_quantity) AS quantity,
           sum(round(remaining_quantity * unit_cost, 2)) AS value,
           bool_or(NOT cost_known) AS unknown
    FROM inventory_cost_layers
    WHERE status = 'OPEN'
    GROUP BY company_id, branch_id, company_product_id
) l ON l.company_id = b.company_id AND l.branch_id = b.branch_id AND l.company_product_id = b.company_product_id
WHERE COALESCE(b.quantity, -1) <> COALESCE(l.quantity, 0)
   OR COALESCE(b.inventory_value, -1) <> COALESCE(l.value, 0)
   OR COALESCE(b.has_unknown_cost, NOT COALESCE(l.unknown, false)) <> COALESCE(l.unknown, false)
"""


def create_opening_layers(connection) -> int:
    """Crea las capas de apertura que falten (determinista; nunca duplica). Devuelve cuántas creó."""
    created = connection.execute(sa.text(OPENING_INSERT)).rowcount
    connection.execute(sa.text(BALANCE_VALUATION_UPDATE))
    return created


def verify_opening_layers(connection) -> None:
    """Σ capas abiertas = cantidad y valor de cada saldo; si no, `OpeningLayersMismatch`."""
    mismatches = connection.execute(sa.text(MISMATCH_QUERY)).scalar_one()
    if mismatches:
        raise OpeningLayersMismatch(
            f"{mismatches} saldo(s) no coinciden con la suma de sus capas abiertas; la migración se revierte."
        )


# ----------------------------------------------------------------------------------
# Restricciones de la Fase A que cambian
# ----------------------------------------------------------------------------------

OPERATION_TYPE_013 = "operation_type IN ('ENTRY','OUTPUT','ENTRY_REVERSAL','OUTPUT_REVERSAL','ADJUSTMENT')"
OPERATION_ORIGIN_013 = (
    "(operation_type IN ('ENTRY','ENTRY_REVERSAL') AND origin_type = 'PURCHASE') "
    "OR (operation_type IN ('OUTPUT','OUTPUT_REVERSAL') AND origin_type = 'SALE') "
    "OR (operation_type = 'ADJUSTMENT' AND origin_type IN ('ADJUSTMENT','COUNT'))"
)
OPERATION_LINES_013 = "line_count BETWEEN 1 AND 100 OR (origin_type = 'COUNT' AND line_count BETWEEN 1 AND 1000)"
MOVEMENT_TYPE_013 = (
    "movement_type IN ('PURCHASE_ENTRY','SALE_OUTPUT','ENTRY_REVERSAL','OUTPUT_REVERSAL',"
    "'POSITIVE_ADJUSTMENT','NEGATIVE_ADJUSTMENT')"
)
MOVEMENT_MATH_013 = (
    "(movement_type IN ('PURCHASE_ENTRY','OUTPUT_REVERSAL','POSITIVE_ADJUSTMENT') "
    "AND new_balance = previous_balance + quantity) "
    "OR (movement_type IN ('SALE_OUTPUT','ENTRY_REVERSAL','NEGATIVE_ADJUSTMENT') "
    "AND new_balance = previous_balance - quantity)"
)
MOVEMENT_UNIT_COST_013 = "unit_cost IS NULL OR unit_cost >= 0"

OPERATION_TYPE_012 = "operation_type IN ('ENTRY','OUTPUT','ENTRY_REVERSAL','OUTPUT_REVERSAL')"
OPERATION_ORIGIN_012 = (
    "(operation_type IN ('ENTRY','ENTRY_REVERSAL') AND origin_type = 'PURCHASE') "
    "OR (operation_type IN ('OUTPUT','OUTPUT_REVERSAL') AND origin_type = 'SALE')"
)
OPERATION_LINES_012 = "line_count BETWEEN 1 AND 100"
MOVEMENT_TYPE_012 = "movement_type IN ('PURCHASE_ENTRY','SALE_OUTPUT','ENTRY_REVERSAL','OUTPUT_REVERSAL')"
MOVEMENT_MATH_012 = (
    "(movement_type IN ('PURCHASE_ENTRY','OUTPUT_REVERSAL') AND new_balance = previous_balance + quantity) "
    "OR (movement_type IN ('SALE_OUTPUT','ENTRY_REVERSAL') AND new_balance = previous_balance - quantity)"
)
MOVEMENT_UNIT_COST_012 = (
    "unit_cost IS NULL OR (unit_cost >= 0 AND movement_type IN ('PURCHASE_ENTRY','ENTRY_REVERSAL'))"
)

IMMUTABLE_TABLES = ("inventory_adjustments", "inventory_cost_consumptions")


def upgrade() -> None:
    # Fase A ------------------------------------------------------------------------
    _replace_check("inventory_operations", "ck_inventory_operations_type", OPERATION_TYPE_013)
    _replace_check("inventory_operations", "ck_inventory_operations_origin_type", OPERATION_ORIGIN_013)
    _replace_check("inventory_operations", "ck_inventory_operations_line_count", OPERATION_LINES_013)

    op.add_column("inventory_movements", sa.Column("movement_value", MONEY, nullable=True))
    op.add_column("inventory_movements", sa.Column("cost_known", sa.Boolean(), nullable=True))
    _replace_check("inventory_movements", "ck_inventory_movements_type", MOVEMENT_TYPE_013)
    _replace_check("inventory_movements", "ck_inventory_movements_balance_math", MOVEMENT_MATH_013)
    _replace_check("inventory_movements", "ck_inventory_movements_unit_cost", MOVEMENT_UNIT_COST_013)
    op.create_check_constraint(
        op.f("ck_inventory_movements_movement_value_non_negative"),
        "inventory_movements",
        "movement_value IS NULL OR movement_value >= 0",
    )
    op.execute(
        "ALTER TABLE inventory_movements ADD CONSTRAINT ck_inventory_movements_valued "
        "CHECK (unit_cost IS NOT NULL AND movement_value IS NOT NULL AND cost_known IS NOT NULL) NOT VALID"
    )

    op.add_column("inventory_balances", sa.Column("average_unit_cost", QUANTITY, nullable=True))
    op.add_column(
        "inventory_balances", sa.Column("inventory_value", MONEY, nullable=False, server_default=sa.text("0"))
    )
    op.add_column(
        "inventory_balances",
        sa.Column("has_unknown_cost", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_check_constraint(
        op.f("ck_inventory_balances_inventory_value_non_negative"), "inventory_balances", "inventory_value >= 0"
    )

    # Políticas -----------------------------------------------------------------------
    op.create_table(
        "company_inventory_policies",
        _id(),
        _uuid("company_id"),
        sa.Column("inventory_system", sa.String(20), nullable=False),
        sa.Column("valuation_method", sa.String(30), nullable=False, server_default=sa.text("'FIFO'")),
        sa.Column("replenishment_strategy", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_inventory_policies")),
        sa.UniqueConstraint("company_id", name=op.f("uq_company_inventory_policies_company")),
        sa.CheckConstraint(
            "inventory_system IN ('PERPETUAL','PERIODIC')", name=op.f("ck_company_inventory_policies_system")
        ),
        sa.CheckConstraint("valuation_method = 'FIFO'", name=op.f("ck_company_inventory_policies_valuation_fifo")),
        sa.CheckConstraint(
            "replenishment_strategy IN ('STANDARD','JIT')", name=op.f("ck_company_inventory_policies_replenishment")
        ),
    )

    op.create_table(
        "inventory_policies",
        _id(),
        _uuid("company_id"),
        _uuid("branch_id"),
        _uuid("company_product_id"),
        sa.Column("minimum_stock", QUANTITY, nullable=False, server_default=sa.text("0")),
        sa.Column("target_stock", QUANTITY, nullable=True),
        sa.Column("service_level", sa.Numeric(7, 4), nullable=True),
        sa.Column("safety_stock_method", sa.String(20), nullable=False),
        sa.Column("calculation_window_days", sa.Integer(), nullable=False, server_default=sa.text("90")),
        sa.Column("replenishment_mode", sa.String(20), nullable=False),
        sa.Column("auto_purchase_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_policies")),
        sa.CheckConstraint(
            "minimum_stock >= 0 AND (target_stock IS NULL OR target_stock >= minimum_stock)",
            name=op.f("ck_inventory_policies_levels"),
        ),
        sa.CheckConstraint(
            "service_level IS NULL OR (service_level > 0 AND service_level < 1)",
            name=op.f("ck_inventory_policies_service_level"),
        ),
        sa.CheckConstraint("calculation_window_days BETWEEN 1 AND 3650", name=op.f("ck_inventory_policies_window")),
        sa.CheckConstraint(
            "safety_stock_method IN ('BASIC','STATISTICAL')", name=op.f("ck_inventory_policies_safety_method")
        ),
        sa.CheckConstraint("replenishment_mode IN ('MANUAL','AUTO_DRAFT')", name=op.f("ck_inventory_policies_mode")),
    )
    op.create_index(
        "uq_inventory_policies_active",
        "inventory_policies",
        ["company_id", "branch_id", "company_product_id"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    # Conteos (antes que ajustes: el ajuste referencia el conteo) ----------------------
    op.create_table(
        "inventory_counts",
        _id(),
        _uuid("company_id"),
        _uuid("branch_id"),
        sa.Column("status", sa.String(20), nullable=False),
        _uuid("started_by_user_id"),
        _timestamp("started_at", nullable=True),
        _uuid("completed_by_user_id", nullable=True),
        _timestamp("completed_at", nullable=True),
        _uuid("cancelled_by_user_id", nullable=True),
        _timestamp("cancelled_at", nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        _uuid("operation_id", nullable=True),
        sa.Column("observations", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        *_audit(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_counts")),
        sa.ForeignKeyConstraint(["operation_id"], ["inventory_operations.id"], name=op.f("fk_inventory_counts_operation")),
        sa.CheckConstraint(
            "status IN ('DRAFT','IN_PROGRESS','COMPLETED','CANCELLED')", name=op.f("ck_inventory_counts_status")
        ),
        sa.CheckConstraint(
            "(status = 'DRAFT' AND started_at IS NULL AND completed_by_user_id IS NULL AND completed_at IS NULL "
            "AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL AND operation_id IS NULL) "
            "OR (status = 'IN_PROGRESS' AND started_at IS NOT NULL AND completed_by_user_id IS NULL AND completed_at IS NULL "
            "AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL AND operation_id IS NULL) "
            "OR (status = 'COMPLETED' AND started_at IS NOT NULL AND completed_by_user_id IS NOT NULL "
            "AND completed_at IS NOT NULL "
            "AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) "
            "OR (status = 'CANCELLED' AND cancelled_by_user_id IS NOT NULL AND cancelled_at IS NOT NULL "
            "AND cancel_reason IS NOT NULL AND completed_by_user_id IS NULL AND completed_at IS NULL AND operation_id IS NULL)",
            name=op.f("ck_inventory_counts_lifecycle"),
        ),
    )
    op.create_index(
        "uq_inventory_counts_in_progress",
        "inventory_counts",
        ["company_id", "branch_id"],
        unique=True,
        postgresql_where=sa.text("status = 'IN_PROGRESS'"),
    )
    op.create_index("ix_inventory_counts_company", "inventory_counts", ["company_id", "branch_id", sa.text("created_at DESC")])

    # Ajustes --------------------------------------------------------------------------
    op.create_table(
        "inventory_adjustments",
        _id(),
        _uuid("operation_id"),
        _uuid("movement_id"),
        _uuid("company_id"),
        _uuid("branch_id"),
        _uuid("company_product_id"),
        sa.Column("adjustment_type", sa.String(30), nullable=False),
        sa.Column("quantity", QUANTITY, nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("previous_balance", QUANTITY, nullable=False),
        sa.Column("new_balance", QUANTITY, nullable=False),
        sa.Column("unit_cost", QUANTITY, nullable=False),
        sa.Column("adjustment_value", MONEY, nullable=False),
        _uuid("inventory_count_id", nullable=True),
        _uuid("application_user_id"),
        *_audit(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_adjustments")),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["inventory_operations.id"], name=op.f("fk_inventory_adjustments_operation")
        ),
        sa.ForeignKeyConstraint(["movement_id"], ["inventory_movements.id"], name=op.f("fk_inventory_adjustments_movement")),
        sa.UniqueConstraint("movement_id", name=op.f("uq_inventory_adjustments_movement")),
        sa.ForeignKeyConstraint(["inventory_count_id"], ["inventory_counts.id"], name=op.f("fk_inventory_adjustments_count")),
        sa.CheckConstraint("adjustment_type IN ('POSITIVE','NEGATIVE')", name=op.f("ck_inventory_adjustments_type")),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_inventory_adjustments_quantity_positive")),
        sa.CheckConstraint(
            "btrim(reason) <> '' AND reason = btrim(reason) AND char_length(reason) <= 2000",
            name=op.f("ck_inventory_adjustments_reason"),
        ),
        sa.CheckConstraint(
            "previous_balance >= 0 AND new_balance >= 0 AND ("
            "(adjustment_type = 'POSITIVE' AND new_balance = previous_balance + quantity) "
            "OR (adjustment_type = 'NEGATIVE' AND new_balance = previous_balance - quantity))",
            name=op.f("ck_inventory_adjustments_balance_math"),
        ),
        sa.CheckConstraint(
            "unit_cost >= 0 AND adjustment_value >= 0", name=op.f("ck_inventory_adjustments_values_non_negative")
        ),
        sa.CheckConstraint(
            "updated_at = created_at AND updated_by = created_by",
            name=op.f("ck_inventory_adjustments_audit_unchanged"),
        ),
    )
    op.create_index(
        "ix_inventory_adjustments_company",
        "inventory_adjustments",
        ["company_id", sa.text("created_at DESC"), sa.text("id DESC")],
    )

    op.create_table(
        "inventory_count_details",
        _id(),
        _uuid("inventory_count_id"),
        _uuid("company_product_id"),
        sa.Column("system_quantity_snapshot", QUANTITY, nullable=False),
        sa.Column("counted_quantity", QUANTITY, nullable=False),
        sa.Column("difference_quantity", QUANTITY, nullable=False),
        sa.Column("unit_cost", QUANTITY, nullable=True),
        _uuid("inventory_adjustment_id", nullable=True),
        _uuid("counted_by_user_id"),
        sa.Column("counted_at", sa.DateTime(timezone=True), nullable=False),
        *_audit(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_count_details")),
        sa.ForeignKeyConstraint(
            ["inventory_count_id"], ["inventory_counts.id"], name=op.f("fk_inventory_count_details_count")
        ),
        sa.ForeignKeyConstraint(
            ["inventory_adjustment_id"],
            ["inventory_adjustments.id"],
            name=op.f("fk_inventory_count_details_adjustment"),
        ),
        sa.UniqueConstraint(
            "inventory_count_id", "company_product_id", name=op.f("uq_inventory_count_details_product")
        ),
        sa.CheckConstraint(
            "system_quantity_snapshot >= 0 AND counted_quantity >= 0 AND (unit_cost IS NULL OR unit_cost >= 0)",
            name=op.f("ck_inventory_count_details_quantities"),
        ),
        sa.CheckConstraint(
            "difference_quantity = counted_quantity - system_quantity_snapshot",
            name=op.f("ck_inventory_count_details_difference"),
        ),
    )

    # Valoración FIFO --------------------------------------------------------------------
    op.create_table(
        "inventory_cost_layers",
        _id(),
        _uuid("company_id"),
        _uuid("branch_id"),
        _uuid("company_product_id"),
        sa.Column("layer_kind", sa.String(20), nullable=False),
        _uuid("origin_movement_id", nullable=True),
        _uuid("origin_purchase_id", nullable=True),
        _uuid("origin_purchase_detail_id", nullable=True),
        sa.Column("original_quantity", QUANTITY, nullable=False),
        sa.Column("remaining_quantity", QUANTITY, nullable=False),
        sa.Column("unit_cost", QUANTITY, nullable=False),
        sa.Column("cost_known", sa.Boolean(), nullable=False),
        sa.Column("currency_code", sa.CHAR(3), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        *_audit(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_cost_layers")),
        sa.ForeignKeyConstraint(
            ["origin_movement_id"], ["inventory_movements.id"], name=op.f("fk_inventory_cost_layers_origin_movement")
        ),
        sa.UniqueConstraint("origin_movement_id", name=op.f("uq_inventory_cost_layers_origin_movement")),
        sa.CheckConstraint("layer_kind IN ('ENTRY','ADJUSTMENT','OPENING')", name=op.f("ck_inventory_cost_layers_kind")),
        sa.CheckConstraint(
            "(layer_kind = 'OPENING') = (origin_movement_id IS NULL)", name=op.f("ck_inventory_cost_layers_origin")
        ),
        sa.CheckConstraint(
            "original_quantity > 0 AND remaining_quantity >= 0 AND remaining_quantity <= original_quantity",
            name=op.f("ck_inventory_cost_layers_quantities"),
        ),
        sa.CheckConstraint(
            "(status = 'OPEN' AND remaining_quantity > 0) OR (status = 'CLOSED' AND remaining_quantity = 0)",
            name=op.f("ck_inventory_cost_layers_status_matches_remaining"),
        ),
        sa.CheckConstraint("unit_cost >= 0", name=op.f("ck_inventory_cost_layers_unit_cost")),
        sa.CheckConstraint(
            "(currency_code IS NULL AND layer_kind = 'OPENING') OR (currency_code IS NOT NULL AND currency_code ~ '^[A-Z]{3}$')",
            name=op.f("ck_inventory_cost_layers_currency"),
        ),
        sa.CheckConstraint(
            "(cost_known OR layer_kind = 'OPENING') AND (cost_known OR unit_cost = 0)",
            name=op.f("ck_inventory_cost_layers_cost_known"),
        ),
    )
    op.create_index(
        "ix_inventory_cost_layers_open",
        "inventory_cost_layers",
        ["company_id", "branch_id", "company_product_id", "received_at", "id"],
        postgresql_where=sa.text("status = 'OPEN'"),
    )
    op.create_index(
        "ix_inventory_cost_layers_product",
        "inventory_cost_layers",
        ["company_id", "branch_id", "company_product_id", "received_at", "id"],
    )
    op.create_index(
        "uq_inventory_cost_layers_opening",
        "inventory_cost_layers",
        ["company_id", "branch_id", "company_product_id"],
        unique=True,
        postgresql_where=sa.text("layer_kind = 'OPENING'"),
    )

    op.create_table(
        "inventory_cost_consumptions",
        _id(),
        _uuid("movement_id"),
        _uuid("cost_layer_id"),
        sa.Column("consumption_type", sa.String(20), nullable=False),
        _uuid("restores_consumption_id", nullable=True),
        sa.Column("quantity", QUANTITY, nullable=False),
        sa.Column("unit_cost", QUANTITY, nullable=False),
        sa.Column("cost_known", sa.Boolean(), nullable=False),
        sa.Column("cost_amount", MONEY, nullable=False),
        _timestamp("created_at"),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_cost_consumptions")),
        sa.ForeignKeyConstraint(
            ["movement_id"], ["inventory_movements.id"], name=op.f("fk_inventory_cost_consumptions_movement")
        ),
        sa.ForeignKeyConstraint(
            ["cost_layer_id"], ["inventory_cost_layers.id"], name=op.f("fk_inventory_cost_consumptions_layer")
        ),
        sa.ForeignKeyConstraint(
            ["restores_consumption_id"],
            ["inventory_cost_consumptions.id"],
            name=op.f("fk_inventory_cost_consumptions_restores"),
        ),
        sa.UniqueConstraint("restores_consumption_id", name=op.f("uq_inventory_cost_consumptions_restores")),
        sa.CheckConstraint(
            "consumption_type IN ('CONSUME','RESTORE','ENTRY_REVERSAL')",
            name=op.f("ck_inventory_cost_consumptions_type"),
        ),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_inventory_cost_consumptions_quantity_positive")),
        sa.CheckConstraint(
            "(consumption_type = 'RESTORE') = (restores_consumption_id IS NOT NULL)",
            name=op.f("ck_inventory_cost_consumptions_restore_link"),
        ),
    )
    op.create_index("ix_inventory_cost_consumptions_movement", "inventory_cost_consumptions", ["movement_id"])
    op.create_index("ix_inventory_cost_consumptions_layer", "inventory_cost_consumptions", ["cost_layer_id"])

    # Inmutabilidad (R-12) -----------------------------------------------------------------
    for table in IMMUTABLE_TABLES:
        for action, event in (("no_update", "UPDATE"), ("no_delete", "DELETE")):
            op.execute(
                f"CREATE TRIGGER tr_{table}_{action} BEFORE {event} ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION inventory_reject_change()"
            )
        op.execute(
            f"CREATE TRIGGER tr_{table}_no_truncate BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION inventory_reject_change()"
        )
    op.execute(
        "CREATE TRIGGER tr_inventory_cost_layers_no_delete BEFORE DELETE ON inventory_cost_layers "
        "FOR EACH ROW EXECUTE FUNCTION inventory_reject_change()"
    )
    op.execute(
        "CREATE TRIGGER tr_inventory_cost_layers_no_truncate BEFORE TRUNCATE ON inventory_cost_layers "
        "FOR EACH STATEMENT EXECUTE FUNCTION inventory_reject_change()"
    )
    op.execute(
        """
        CREATE FUNCTION inventory_count_details_guard() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            parent_status text;
        BEGIN
            SELECT status INTO parent_status FROM inventory_counts WHERE id = OLD.inventory_count_id;
            IF parent_status IN ('COMPLETED', 'CANCELLED') THEN
                RAISE EXCEPTION '% no permitido sobre %: el conteo está finalizado y sus detalles son inmutables',
                    TG_OP, TG_TABLE_NAME
                    USING ERRCODE = 'restrict_violation';
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER tr_inventory_count_details_finalized BEFORE UPDATE OR DELETE ON inventory_count_details "
        "FOR EACH ROW EXECUTE FUNCTION inventory_count_details_guard()"
    )

    # Capa de apertura de los saldos de la Fase A (R-05) ----------------------------------
    connection = op.get_bind()
    create_opening_layers(connection)
    verify_opening_layers(connection)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS tr_inventory_count_details_finalized ON inventory_count_details")
    op.execute("DROP FUNCTION IF EXISTS inventory_count_details_guard()")
    for table in (*IMMUTABLE_TABLES, "inventory_cost_layers"):
        for action in ("no_update", "no_delete", "no_truncate"):
            op.execute(f"DROP TRIGGER IF EXISTS tr_{table}_{action} ON {table}")

    op.drop_index("ix_inventory_cost_consumptions_layer", table_name="inventory_cost_consumptions")
    op.drop_index("ix_inventory_cost_consumptions_movement", table_name="inventory_cost_consumptions")
    op.drop_table("inventory_cost_consumptions")
    op.drop_index("uq_inventory_cost_layers_opening", table_name="inventory_cost_layers")
    op.drop_index("ix_inventory_cost_layers_product", table_name="inventory_cost_layers")
    op.drop_index("ix_inventory_cost_layers_open", table_name="inventory_cost_layers")
    op.drop_table("inventory_cost_layers")
    op.drop_table("inventory_count_details")
    op.drop_index("ix_inventory_adjustments_company", table_name="inventory_adjustments")
    op.drop_table("inventory_adjustments")
    op.drop_index("ix_inventory_counts_company", table_name="inventory_counts")
    op.drop_index("uq_inventory_counts_in_progress", table_name="inventory_counts")
    op.drop_table("inventory_counts")
    op.drop_index("uq_inventory_policies_active", table_name="inventory_policies")
    op.drop_table("inventory_policies")
    op.drop_table("company_inventory_policies")

    op.drop_constraint(op.f("ck_inventory_balances_inventory_value_non_negative"), "inventory_balances", type_="check")
    op.drop_column("inventory_balances", "has_unknown_cost")
    op.drop_column("inventory_balances", "inventory_value")
    op.drop_column("inventory_balances", "average_unit_cost")

    op.drop_constraint(op.f("ck_inventory_movements_valued"), "inventory_movements", type_="check")
    op.drop_constraint(op.f("ck_inventory_movements_movement_value_non_negative"), "inventory_movements", type_="check")
    _replace_check("inventory_movements", "ck_inventory_movements_unit_cost", MOVEMENT_UNIT_COST_012)
    _replace_check("inventory_movements", "ck_inventory_movements_balance_math", MOVEMENT_MATH_012)
    _replace_check("inventory_movements", "ck_inventory_movements_type", MOVEMENT_TYPE_012)
    op.drop_column("inventory_movements", "cost_known")
    op.drop_column("inventory_movements", "movement_value")

    _replace_check("inventory_operations", "ck_inventory_operations_line_count", OPERATION_LINES_012)
    _replace_check("inventory_operations", "ck_inventory_operations_origin_type", OPERATION_ORIGIN_012)
    _replace_check("inventory_operations", "ck_inventory_operations_type", OPERATION_TYPE_012)
