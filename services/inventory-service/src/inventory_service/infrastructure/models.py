"""Modelos SQLAlchemy de Inventory Service (`specs/012-inventory-core/data-model.md`).

La migración `alembic/versions/0001_inventory_core.py` es la fuente del esquema;
estos modelos reflejan las mismas columnas y restricciones con nombre explícito
(`conv`, sin reaplicar la convención). Sin `version_id_col`: el saldo se serializa
con `SELECT … FOR UPDATE` y `version` es su contador de movimientos (R-04).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sio_audit.outbox import audit_outbox_table
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import CHAR
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.naming import conv

from inventory_service.infrastructure.database import Base

QUANTITY = Numeric(18, 4)

OPERATION_TYPES_SQL = "('ENTRY','OUTPUT','ENTRY_REVERSAL','OUTPUT_REVERSAL')"
MOVEMENT_TYPES_SQL = "('PURCHASE_ENTRY','SALE_OUTPUT','ENTRY_REVERSAL','OUTPUT_REVERSAL')"

OPERATION_ORIGIN_TYPE_CHECK = (
    "(operation_type IN ('ENTRY','ENTRY_REVERSAL') AND origin_type = 'PURCHASE') "
    "OR (operation_type IN ('OUTPUT','OUTPUT_REVERSAL') AND origin_type = 'SALE')"
)
OPERATION_REVERSAL_LINK_CHECK = (
    "(reverses_operation_id IS NOT NULL) = (operation_type IN ('ENTRY_REVERSAL','OUTPUT_REVERSAL'))"
)
OPERATION_REASON_CHECK = (
    "(reason IS NULL OR (btrim(reason) <> '' AND reason = btrim(reason) AND char_length(reason) <= 2000)) "
    "AND (operation_type NOT IN ('ENTRY_REVERSAL','OUTPUT_REVERSAL') OR reason IS NOT NULL)"
)
MOVEMENT_BALANCE_MATH_CHECK = (
    "(movement_type IN ('PURCHASE_ENTRY','OUTPUT_REVERSAL') AND new_balance = previous_balance + quantity) "
    "OR (movement_type IN ('SALE_OUTPUT','ENTRY_REVERSAL') AND new_balance = previous_balance - quantity)"
)
MOVEMENT_UNIT_COST_CHECK = (
    "unit_cost IS NULL OR (unit_cost >= 0 AND movement_type IN ('PURCHASE_ENTRY','ENTRY_REVERSAL'))"
)
MOVEMENT_REVERSAL_LINK_CHECK = (
    "(reversed_movement_id IS NOT NULL) = (movement_type IN ('ENTRY_REVERSAL','OUTPUT_REVERSAL'))"
)


class InventoryOperation(Base):
    """Operación aplicada o reverso; solo inserción (R-03, R-06)."""

    __tablename__ = "inventory_operations"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("pk_inventory_operations")),
        UniqueConstraint("operation_key", name=conv("uq_inventory_operations_operation_key")),
        UniqueConstraint("reverses_operation_id", name=conv("uq_inventory_operations_reverses")),
        ForeignKeyConstraint(
            ["reverses_operation_id"],
            ["inventory_operations.id"],
            name=conv("fk_inventory_operations_reverses"),
        ),
        CheckConstraint(f"operation_type IN {OPERATION_TYPES_SQL}", name=conv("ck_inventory_operations_type")),
        CheckConstraint(OPERATION_ORIGIN_TYPE_CHECK, name=conv("ck_inventory_operations_origin_type")),
        CheckConstraint(OPERATION_REVERSAL_LINK_CHECK, name=conv("ck_inventory_operations_reversal_link")),
        CheckConstraint(OPERATION_REASON_CHECK, name=conv("ck_inventory_operations_reason")),
        CheckConstraint("line_count BETWEEN 1 AND 100", name=conv("ck_inventory_operations_line_count")),
        CheckConstraint(
            "request_hash ~ '^[0-9a-f]{64}$'", name=conv("ck_inventory_operations_request_hash_format")
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    operation_key: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    requested_by_client: Mapped[str] = mapped_column(String(80), nullable=False)
    operation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    company_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    origin_type: Mapped[str] = mapped_column(String(30), nullable=False)
    origin_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    application_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reverses_operation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    line_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    request_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


class InventoryBalance(Base):
    """Saldo vigente por empresa, sucursal y producto (§9.1, DS-10)."""

    __tablename__ = "inventory_balances"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("pk_inventory_balances")),
        UniqueConstraint(
            "company_id", "branch_id", "company_product_id", name=conv("uq_inventory_balances_product")
        ),
        CheckConstraint("quantity >= 0", name=conv("ck_inventory_balances_quantity_non_negative")),
        CheckConstraint("version >= 0", name=conv("ck_inventory_balances_version_non_negative")),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    company_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


class InventoryMovement(Base):
    """Movimiento inmutable del kardex (§9.2, DS-10)."""

    __tablename__ = "inventory_movements"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("pk_inventory_movements")),
        ForeignKeyConstraint(
            ["operation_id"], ["inventory_operations.id"], name=conv("fk_inventory_movements_operation")
        ),
        ForeignKeyConstraint(
            ["reversed_movement_id"],
            ["inventory_movements.id"],
            name=conv("fk_inventory_movements_reversed"),
        ),
        UniqueConstraint(
            "company_id",
            "branch_id",
            "company_product_id",
            "balance_sequence",
            name=conv("uq_inventory_movements_sequence"),
        ),
        UniqueConstraint("operation_id", "line_index", name=conv("uq_inventory_movements_operation_line")),
        UniqueConstraint("reversed_movement_id", name=conv("uq_inventory_movements_reversed")),
        CheckConstraint(f"movement_type IN {MOVEMENT_TYPES_SQL}", name=conv("ck_inventory_movements_type")),
        CheckConstraint("quantity > 0", name=conv("ck_inventory_movements_quantity_positive")),
        CheckConstraint(
            "previous_balance >= 0 AND new_balance >= 0",
            name=conv("ck_inventory_movements_balances_non_negative"),
        ),
        CheckConstraint(MOVEMENT_BALANCE_MATH_CHECK, name=conv("ck_inventory_movements_balance_math")),
        CheckConstraint(MOVEMENT_UNIT_COST_CHECK, name=conv("ck_inventory_movements_unit_cost")),
        CheckConstraint(MOVEMENT_REVERSAL_LINK_CHECK, name=conv("ck_inventory_movements_reversal_link")),
        CheckConstraint(
            "updated_at = created_at AND updated_by = created_by",
            name=conv("ck_inventory_movements_audit_unchanged"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    operation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    company_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    previous_balance: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    new_balance: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    balance_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(QUANTITY, nullable=True)
    origin_type: Mapped[str] = mapped_column(String(30), nullable=False)
    origin_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    origin_detail_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    line_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    application_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    correlation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reversed_movement_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


AUDIT_OUTBOX = audit_outbox_table(Base.metadata)
"""Outbox de auditoría (`libs/sio-audit`; categoría Outbox, D26)."""
