"""Modelos SQLAlchemy de Inventory Service (`specs/012-inventory-core/data-model.md` y 013).

Las migraciones `0001_inventory_core.py` y `0002_inventory_complementary.py` son la fuente del esquema;
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
    Boolean,
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

MONEY = Numeric(18, 2)

OPERATION_TYPES_SQL = "('ENTRY','OUTPUT','ENTRY_REVERSAL','OUTPUT_REVERSAL','ADJUSTMENT')"
MOVEMENT_TYPES_SQL = (
    "('PURCHASE_ENTRY','SALE_OUTPUT','ENTRY_REVERSAL','OUTPUT_REVERSAL','POSITIVE_ADJUSTMENT','NEGATIVE_ADJUSTMENT')"
)

OPERATION_ORIGIN_TYPE_CHECK = (
    "(operation_type IN ('ENTRY','ENTRY_REVERSAL') AND origin_type = 'PURCHASE') "
    "OR (operation_type IN ('OUTPUT','OUTPUT_REVERSAL') AND origin_type = 'SALE') "
    "OR (operation_type = 'ADJUSTMENT' AND origin_type IN ('ADJUSTMENT','COUNT'))"
)
OPERATION_LINE_COUNT_CHECK = (
    "line_count BETWEEN 1 AND 100 OR (origin_type = 'COUNT' AND line_count BETWEEN 1 AND 1000)"
)
OPERATION_REVERSAL_LINK_CHECK = (
    "(reverses_operation_id IS NOT NULL) = (operation_type IN ('ENTRY_REVERSAL','OUTPUT_REVERSAL'))"
)
OPERATION_REASON_CHECK = (
    "(reason IS NULL OR (btrim(reason) <> '' AND reason = btrim(reason) AND char_length(reason) <= 2000)) "
    "AND (operation_type NOT IN ('ENTRY_REVERSAL','OUTPUT_REVERSAL') OR reason IS NOT NULL)"
)
MOVEMENT_BALANCE_MATH_CHECK = (
    "(movement_type IN ('PURCHASE_ENTRY','OUTPUT_REVERSAL','POSITIVE_ADJUSTMENT') "
    "AND new_balance = previous_balance + quantity) "
    "OR (movement_type IN ('SALE_OUTPUT','ENTRY_REVERSAL','NEGATIVE_ADJUSTMENT') "
    "AND new_balance = previous_balance - quantity)"
)
MOVEMENT_UNIT_COST_CHECK = "unit_cost IS NULL OR unit_cost >= 0"
MOVEMENT_VALUED_CHECK = "unit_cost IS NOT NULL AND movement_value IS NOT NULL AND cost_known IS NOT NULL"
"""Toda fila nueva valorizada. En la base es `NOT VALID`: no revalida el historial de la Fase A (013 R-03)."""
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
        CheckConstraint(OPERATION_LINE_COUNT_CHECK, name=conv("ck_inventory_operations_line_count")),
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
        CheckConstraint("inventory_value >= 0", name=conv("ck_inventory_balances_inventory_value_non_negative")),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    company_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    average_unit_cost: Mapped[Decimal | None] = mapped_column(QUANTITY, nullable=True)
    inventory_value: Mapped[Decimal] = mapped_column(MONEY, nullable=False, server_default=text("0"))
    has_unknown_cost: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
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
        CheckConstraint(
            "movement_value IS NULL OR movement_value >= 0",
            name=conv("ck_inventory_movements_movement_value_non_negative"),
        ),
        CheckConstraint(MOVEMENT_VALUED_CHECK, name=conv("ck_inventory_movements_valued")),
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
    movement_value: Mapped[Decimal | None] = mapped_column(MONEY, nullable=True)
    cost_known: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
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


# ==========================================================================
# Fase B (013): `specs/013-inventory-complementary/data-model.md`
# ==========================================================================

ADJUSTMENT_REASON_CHECK = "btrim(reason) <> '' AND reason = btrim(reason) AND char_length(reason) <= 2000"
ADJUSTMENT_BALANCE_MATH_CHECK = (
    "previous_balance >= 0 AND new_balance >= 0 AND ("
    "(adjustment_type = 'POSITIVE' AND new_balance = previous_balance + quantity) "
    "OR (adjustment_type = 'NEGATIVE' AND new_balance = previous_balance - quantity))"
)
COUNT_LIFECYCLE_CHECK = (
    "(status = 'DRAFT' AND started_at IS NULL AND completed_by_user_id IS NULL AND completed_at IS NULL "
    "AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL AND operation_id IS NULL) "
    "OR (status = 'IN_PROGRESS' AND started_at IS NOT NULL AND completed_by_user_id IS NULL AND completed_at IS NULL "
    "AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL AND operation_id IS NULL) "
    "OR (status = 'COMPLETED' AND started_at IS NOT NULL AND completed_by_user_id IS NOT NULL "
    "AND completed_at IS NOT NULL "
    "AND cancelled_by_user_id IS NULL AND cancelled_at IS NULL AND cancel_reason IS NULL) "
    "OR (status = 'CANCELLED' AND cancelled_by_user_id IS NOT NULL AND cancelled_at IS NOT NULL "
    "AND cancel_reason IS NOT NULL AND completed_by_user_id IS NULL AND completed_at IS NULL AND operation_id IS NULL)"
)
LAYER_CURRENCY_CHECK = (
    "(currency_code IS NULL AND layer_kind = 'OPENING') OR (currency_code IS NOT NULL AND currency_code ~ '^[A-Z]{3}$')"
)
LAYER_COST_KNOWN_CHECK = "(cost_known OR layer_kind = 'OPENING') AND (cost_known OR unit_cost = 0)"


def _created(nullable: bool = False):
    return mapped_column(DateTime(timezone=True), nullable=nullable, server_default=text("now()"))


class CompanyInventoryPolicy(Base):
    """Política de inventario de una empresa (§9.4; R-06; C-07: `is_active` siempre `true`)."""

    __tablename__ = "company_inventory_policies"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("pk_company_inventory_policies")),
        UniqueConstraint("company_id", name=conv("uq_company_inventory_policies_company")),
        CheckConstraint(
            "inventory_system IN ('PERPETUAL','PERIODIC')", name=conv("ck_company_inventory_policies_system")
        ),
        CheckConstraint("valuation_method = 'FIFO'", name=conv("ck_company_inventory_policies_valuation_fifo")),
        CheckConstraint(
            "replenishment_strategy IN ('STANDARD','JIT')", name=conv("ck_company_inventory_policies_replenishment")
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    company_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    inventory_system: Mapped[str] = mapped_column(String(20), nullable=False)
    valuation_method: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'FIFO'"))
    replenishment_strategy: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = _created()
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = _created()
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


class InventoryPolicy(Base):
    """Niveles de reposición de un producto en una sucursal (§9.5; R-07)."""

    __tablename__ = "inventory_policies"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("pk_inventory_policies")),
        CheckConstraint(
            "minimum_stock >= 0 AND (target_stock IS NULL OR target_stock >= minimum_stock)",
            name=conv("ck_inventory_policies_levels"),
        ),
        CheckConstraint(
            "service_level IS NULL OR (service_level > 0 AND service_level < 1)",
            name=conv("ck_inventory_policies_service_level"),
        ),
        CheckConstraint("calculation_window_days BETWEEN 1 AND 3650", name=conv("ck_inventory_policies_window")),
        CheckConstraint(
            "safety_stock_method IN ('BASIC','STATISTICAL')", name=conv("ck_inventory_policies_safety_method")
        ),
        CheckConstraint("replenishment_mode IN ('MANUAL','AUTO_DRAFT')", name=conv("ck_inventory_policies_mode")),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    company_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    minimum_stock: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False, server_default=text("0"))
    target_stock: Mapped[Decimal | None] = mapped_column(QUANTITY, nullable=True)
    service_level: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)
    safety_stock_method: Mapped[str] = mapped_column(String(20), nullable=False)
    calculation_window_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("90"))
    replenishment_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    auto_purchase_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = _created()
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = _created()
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


class InventoryCount(Base):
    """Conteo físico de una sucursal (§9.8; R-10)."""

    __tablename__ = "inventory_counts"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("pk_inventory_counts")),
        ForeignKeyConstraint(["operation_id"], ["inventory_operations.id"], name=conv("fk_inventory_counts_operation")),
        CheckConstraint(
            "status IN ('DRAFT','IN_PROGRESS','COMPLETED','CANCELLED')", name=conv("ck_inventory_counts_status")
        ),
        CheckConstraint(COUNT_LIFECYCLE_CHECK, name=conv("ck_inventory_counts_lifecycle")),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    company_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_by_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    operation_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = _created()
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = _created()
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


class InventoryAdjustment(Base):
    """Ajuste aplicado (§9.3; DS-05, DS-06; C-01: sin `status`). Inmutable."""

    __tablename__ = "inventory_adjustments"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("pk_inventory_adjustments")),
        ForeignKeyConstraint(
            ["operation_id"], ["inventory_operations.id"], name=conv("fk_inventory_adjustments_operation")
        ),
        ForeignKeyConstraint(["movement_id"], ["inventory_movements.id"], name=conv("fk_inventory_adjustments_movement")),
        UniqueConstraint("movement_id", name=conv("uq_inventory_adjustments_movement")),
        ForeignKeyConstraint(
            ["inventory_count_id"], ["inventory_counts.id"], name=conv("fk_inventory_adjustments_count")
        ),
        CheckConstraint("adjustment_type IN ('POSITIVE','NEGATIVE')", name=conv("ck_inventory_adjustments_type")),
        CheckConstraint("quantity > 0", name=conv("ck_inventory_adjustments_quantity_positive")),
        CheckConstraint(ADJUSTMENT_REASON_CHECK, name=conv("ck_inventory_adjustments_reason")),
        CheckConstraint(ADJUSTMENT_BALANCE_MATH_CHECK, name=conv("ck_inventory_adjustments_balance_math")),
        CheckConstraint(
            "unit_cost >= 0 AND adjustment_value >= 0", name=conv("ck_inventory_adjustments_values_non_negative")
        ),
        CheckConstraint(
            "updated_at = created_at AND updated_by = created_by",
            name=conv("ck_inventory_adjustments_audit_unchanged"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    operation_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    movement_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    company_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    adjustment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    previous_balance: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    new_balance: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    adjustment_value: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    inventory_count_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    application_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = _created()
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = _created()
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


class InventoryCountDetail(Base):
    """Producto registrado en un conteo (§9.9; DS-08). Mutable solo con el conteo `IN_PROGRESS`."""

    __tablename__ = "inventory_count_details"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("pk_inventory_count_details")),
        ForeignKeyConstraint(
            ["inventory_count_id"], ["inventory_counts.id"], name=conv("fk_inventory_count_details_count")
        ),
        ForeignKeyConstraint(
            ["inventory_adjustment_id"],
            ["inventory_adjustments.id"],
            name=conv("fk_inventory_count_details_adjustment"),
        ),
        UniqueConstraint(
            "inventory_count_id", "company_product_id", name=conv("uq_inventory_count_details_product")
        ),
        CheckConstraint(
            "system_quantity_snapshot >= 0 AND counted_quantity >= 0 AND (unit_cost IS NULL OR unit_cost >= 0)",
            name=conv("ck_inventory_count_details_quantities"),
        ),
        CheckConstraint(
            "difference_quantity = counted_quantity - system_quantity_snapshot",
            name=conv("ck_inventory_count_details_difference"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    inventory_count_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    system_quantity_snapshot: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    counted_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    difference_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(QUANTITY, nullable=True)
    inventory_adjustment_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    counted_by_user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    counted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = _created()
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = _created()
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


class InventoryCostLayer(Base):
    """Capa de costo FIFO (§9.6; R-03, R-05). Solo el motor cambia su cantidad restante."""

    __tablename__ = "inventory_cost_layers"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("pk_inventory_cost_layers")),
        ForeignKeyConstraint(
            ["origin_movement_id"], ["inventory_movements.id"], name=conv("fk_inventory_cost_layers_origin_movement")
        ),
        UniqueConstraint("origin_movement_id", name=conv("uq_inventory_cost_layers_origin_movement")),
        CheckConstraint("layer_kind IN ('ENTRY','ADJUSTMENT','OPENING')", name=conv("ck_inventory_cost_layers_kind")),
        CheckConstraint(
            "(layer_kind = 'OPENING') = (origin_movement_id IS NULL)", name=conv("ck_inventory_cost_layers_origin")
        ),
        CheckConstraint(
            "original_quantity > 0 AND remaining_quantity >= 0 AND remaining_quantity <= original_quantity",
            name=conv("ck_inventory_cost_layers_quantities"),
        ),
        CheckConstraint(
            "(status = 'OPEN' AND remaining_quantity > 0) OR (status = 'CLOSED' AND remaining_quantity = 0)",
            name=conv("ck_inventory_cost_layers_status_matches_remaining"),
        ),
        CheckConstraint("unit_cost >= 0", name=conv("ck_inventory_cost_layers_unit_cost")),
        CheckConstraint(LAYER_CURRENCY_CHECK, name=conv("ck_inventory_cost_layers_currency")),
        CheckConstraint(LAYER_COST_KNOWN_CHECK, name=conv("ck_inventory_cost_layers_cost_known")),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    company_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    branch_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    company_product_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    layer_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    origin_movement_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    origin_purchase_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    origin_purchase_detail_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    original_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    remaining_quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    cost_known: Mapped[bool] = mapped_column(Boolean, nullable=False)
    currency_code: Mapped[str | None] = mapped_column(CHAR(3), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = _created()
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = _created()
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)


class InventoryCostConsumption(Base):
    """Consumo, restitución o retiro de una capa por un movimiento (§9.7). Inmutable."""

    __tablename__ = "inventory_cost_consumptions"
    __table_args__ = (
        PrimaryKeyConstraint("id", name=conv("pk_inventory_cost_consumptions")),
        ForeignKeyConstraint(
            ["movement_id"], ["inventory_movements.id"], name=conv("fk_inventory_cost_consumptions_movement")
        ),
        ForeignKeyConstraint(
            ["cost_layer_id"], ["inventory_cost_layers.id"], name=conv("fk_inventory_cost_consumptions_layer")
        ),
        ForeignKeyConstraint(
            ["restores_consumption_id"],
            ["inventory_cost_consumptions.id"],
            name=conv("fk_inventory_cost_consumptions_restores"),
        ),
        UniqueConstraint("restores_consumption_id", name=conv("uq_inventory_cost_consumptions_restores")),
        CheckConstraint(
            "consumption_type IN ('CONSUME','RESTORE','ENTRY_REVERSAL')",
            name=conv("ck_inventory_cost_consumptions_type"),
        ),
        CheckConstraint("quantity > 0", name=conv("ck_inventory_cost_consumptions_quantity_positive")),
        CheckConstraint(
            "(consumption_type = 'RESTORE') = (restores_consumption_id IS NOT NULL)",
            name=conv("ck_inventory_cost_consumptions_restore_link"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), server_default=text("gen_random_uuid()"))
    movement_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    cost_layer_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    consumption_type: Mapped[str] = mapped_column(String(20), nullable=False)
    restores_consumption_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(QUANTITY, nullable=False)
    cost_known: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cost_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    created_at: Mapped[datetime] = _created()
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)


AUDIT_OUTBOX = audit_outbox_table(Base.metadata)
"""Outbox de auditoría (`libs/sio-audit`; categoría Outbox, D26)."""
