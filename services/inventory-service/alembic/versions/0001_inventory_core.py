"""Operaciones, saldos y movimientos de inventario, inmutabilidad y outbox de auditoría (012).

- `inventory_operations`: operación aplicada o reverso; idempotencia por
  `operation_key` y `request_hash` (R-03). Solo inserción.
- `inventory_balances`: saldo por empresa, sucursal y producto (§9.1); nunca
  negativo; `version` = número de movimientos aplicados (R-04).
- `inventory_movements`: kardex inmutable (§9.2). `balance_sequence` lo asigna la
  aplicación como `version + 1` tras bloquear el saldo, dentro de la misma
  transacción; NO existe ninguna `SEQUENCE` para él (dejaría huecos tras un
  `ROLLBACK`).
- Triggers que rechazan `UPDATE`/`DELETE`/`TRUNCATE` de movimientos y operaciones y
  `DELETE`/`TRUNCATE` de saldos, también en sesiones manuales (R-06): el rol de la
  aplicación es dueño de las tablas, así que `REVOKE` no las protegería.
- `audit_outbox` de `libs/sio-audit` (FR-071).

`gen_random_uuid()` es nativo en PostgreSQL 17: no se agrega ninguna extensión.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sio_audit.outbox import create_audit_outbox_table, drop_audit_outbox_table
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

QUANTITY = sa.Numeric(18, 4)


def _uuid(name: str, *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def _id() -> sa.Column:
    return sa.Column(
        "id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")
    )


def _timestamp(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))


def upgrade() -> None:
    op.create_table(
        "inventory_operations",
        _id(),
        _uuid("operation_key"),
        sa.Column("requested_by_client", sa.String(80), nullable=False),
        sa.Column("operation_type", sa.String(20), nullable=False),
        _uuid("company_id"),
        _uuid("branch_id"),
        sa.Column("origin_type", sa.String(30), nullable=False),
        _uuid("origin_id"),
        _uuid("application_user_id"),
        _uuid("correlation_id"),
        sa.Column("reason", sa.Text(), nullable=True),
        _uuid("reverses_operation_id", nullable=True),
        sa.Column("line_count", sa.SmallInteger(), nullable=False),
        sa.Column("request_hash", sa.CHAR(64), nullable=False),
        _timestamp("created_at"),
        sa.Column("created_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_operations")),
        sa.UniqueConstraint("operation_key", name=op.f("uq_inventory_operations_operation_key")),
        sa.UniqueConstraint("reverses_operation_id", name=op.f("uq_inventory_operations_reverses")),
        sa.ForeignKeyConstraint(
            ["reverses_operation_id"], ["inventory_operations.id"], name=op.f("fk_inventory_operations_reverses")
        ),
        sa.CheckConstraint(
            "operation_type IN ('ENTRY','OUTPUT','ENTRY_REVERSAL','OUTPUT_REVERSAL')",
            name=op.f("ck_inventory_operations_type"),
        ),
        sa.CheckConstraint(
            "(operation_type IN ('ENTRY','ENTRY_REVERSAL') AND origin_type = 'PURCHASE') "
            "OR (operation_type IN ('OUTPUT','OUTPUT_REVERSAL') AND origin_type = 'SALE')",
            name=op.f("ck_inventory_operations_origin_type"),
        ),
        sa.CheckConstraint(
            "(reverses_operation_id IS NOT NULL) = (operation_type IN ('ENTRY_REVERSAL','OUTPUT_REVERSAL'))",
            name=op.f("ck_inventory_operations_reversal_link"),
        ),
        sa.CheckConstraint(
            "(reason IS NULL OR (btrim(reason) <> '' AND reason = btrim(reason) "
            "AND char_length(reason) <= 2000)) "
            "AND (operation_type NOT IN ('ENTRY_REVERSAL','OUTPUT_REVERSAL') OR reason IS NOT NULL)",
            name=op.f("ck_inventory_operations_reason"),
        ),
        sa.CheckConstraint("line_count BETWEEN 1 AND 100", name=op.f("ck_inventory_operations_line_count")),
        sa.CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'", name=op.f("ck_inventory_operations_request_hash_format")
        ),
    )
    op.create_index(
        "ix_inventory_operations_company",
        "inventory_operations",
        ["company_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "inventory_balances",
        _id(),
        _uuid("company_id"),
        _uuid("branch_id"),
        _uuid("company_product_id"),
        sa.Column("quantity", QUANTITY, nullable=False, server_default=sa.text("0")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        _timestamp("created_at"),
        sa.Column("created_by", sa.String(255), nullable=False),
        _timestamp("updated_at"),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_balances")),
        sa.UniqueConstraint(
            "company_id", "branch_id", "company_product_id", name=op.f("uq_inventory_balances_product")
        ),
        sa.CheckConstraint("quantity >= 0", name=op.f("ck_inventory_balances_quantity_non_negative")),
        sa.CheckConstraint("version >= 0", name=op.f("ck_inventory_balances_version_non_negative")),
    )
    op.create_index(
        "ix_inventory_balances_in_stock",
        "inventory_balances",
        ["company_id", "branch_id"],
        postgresql_where=sa.text("quantity > 0"),
    )

    op.create_table(
        "inventory_movements",
        _id(),
        _uuid("operation_id"),
        _uuid("company_id"),
        _uuid("branch_id"),
        _uuid("company_product_id"),
        sa.Column("movement_type", sa.String(40), nullable=False),
        sa.Column("quantity", QUANTITY, nullable=False),
        sa.Column("previous_balance", QUANTITY, nullable=False),
        sa.Column("new_balance", QUANTITY, nullable=False),
        sa.Column("balance_sequence", sa.BigInteger(), nullable=False),
        sa.Column("unit_cost", QUANTITY, nullable=True),
        sa.Column("origin_type", sa.String(30), nullable=False),
        _uuid("origin_id"),
        _uuid("origin_detail_id"),
        sa.Column("line_index", sa.SmallInteger(), nullable=False),
        _uuid("application_user_id"),
        _uuid("correlation_id"),
        sa.Column("reason", sa.Text(), nullable=True),
        _uuid("reversed_movement_id", nullable=True),
        _timestamp("created_at"),
        sa.Column("created_by", sa.String(255), nullable=False),
        _timestamp("updated_at"),
        sa.Column("updated_by", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_movements")),
        sa.ForeignKeyConstraint(
            ["operation_id"], ["inventory_operations.id"], name=op.f("fk_inventory_movements_operation")
        ),
        sa.ForeignKeyConstraint(
            ["reversed_movement_id"], ["inventory_movements.id"], name=op.f("fk_inventory_movements_reversed")
        ),
        sa.UniqueConstraint(
            "company_id",
            "branch_id",
            "company_product_id",
            "balance_sequence",
            name=op.f("uq_inventory_movements_sequence"),
        ),
        sa.UniqueConstraint("operation_id", "line_index", name=op.f("uq_inventory_movements_operation_line")),
        sa.UniqueConstraint("reversed_movement_id", name=op.f("uq_inventory_movements_reversed")),
        sa.CheckConstraint(
            "movement_type IN ('PURCHASE_ENTRY','SALE_OUTPUT','ENTRY_REVERSAL','OUTPUT_REVERSAL')",
            name=op.f("ck_inventory_movements_type"),
        ),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_inventory_movements_quantity_positive")),
        sa.CheckConstraint(
            "previous_balance >= 0 AND new_balance >= 0",
            name=op.f("ck_inventory_movements_balances_non_negative"),
        ),
        sa.CheckConstraint(
            "(movement_type IN ('PURCHASE_ENTRY','OUTPUT_REVERSAL') AND new_balance = previous_balance + quantity) "
            "OR (movement_type IN ('SALE_OUTPUT','ENTRY_REVERSAL') AND new_balance = previous_balance - quantity)",
            name=op.f("ck_inventory_movements_balance_math"),
        ),
        sa.CheckConstraint(
            "unit_cost IS NULL OR (unit_cost >= 0 AND movement_type IN ('PURCHASE_ENTRY','ENTRY_REVERSAL'))",
            name=op.f("ck_inventory_movements_unit_cost"),
        ),
        sa.CheckConstraint(
            "(reversed_movement_id IS NOT NULL) = (movement_type IN ('ENTRY_REVERSAL','OUTPUT_REVERSAL'))",
            name=op.f("ck_inventory_movements_reversal_link"),
        ),
        sa.CheckConstraint(
            "updated_at = created_at AND updated_by = created_by",
            name=op.f("ck_inventory_movements_audit_unchanged"),
        ),
    )
    op.create_index(
        "ix_inventory_movements_origin", "inventory_movements", ["company_id", "origin_type", "origin_id"]
    )

    op.execute(
        """
        CREATE FUNCTION inventory_reject_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% no permitido sobre %: movimientos y operaciones son inmutables y los saldos no se eliminan',
                TG_OP, TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$
        """
    )
    for table in ("inventory_movements", "inventory_operations"):
        op.execute(
            f"CREATE TRIGGER tr_{table}_no_update BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION inventory_reject_change()"
        )
    for table in ("inventory_movements", "inventory_operations", "inventory_balances"):
        op.execute(
            f"CREATE TRIGGER tr_{table}_no_delete BEFORE DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION inventory_reject_change()"
        )
        op.execute(
            f"CREATE TRIGGER tr_{table}_no_truncate BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION inventory_reject_change()"
        )

    create_audit_outbox_table(op)


def downgrade() -> None:
    drop_audit_outbox_table(op)

    for table in ("inventory_balances", "inventory_operations", "inventory_movements"):
        op.execute(f"DROP TRIGGER IF EXISTS tr_{table}_no_truncate ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS tr_{table}_no_delete ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS tr_{table}_no_update ON {table}")
    op.execute("DROP FUNCTION IF EXISTS inventory_reject_change()")

    op.drop_index("ix_inventory_movements_origin", table_name="inventory_movements")
    op.drop_table("inventory_movements")
    op.drop_index("ix_inventory_balances_in_stock", table_name="inventory_balances")
    op.drop_table("inventory_balances")
    op.drop_index("ix_inventory_operations_company", table_name="inventory_operations")
    op.drop_table("inventory_operations")
